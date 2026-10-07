from uuid import uuid4

from app.db import models
from app.db.base import SessionLocal
from tests.conftest import assert_error_shape


def _profile(name: str = "Tracker Student") -> str:
    with SessionLocal() as db:
        profile = models.Profile(name=name)
        db.add(profile)
        db.commit()
        return profile.id


def _create(client, pid: str, **kw) -> dict:
    body = {"profile_id": pid, "company": "Northwind Labs", "title": "Backend Intern", **kw}
    res = client.post("/v1/applications", json=body)
    assert res.status_code == 201, res.text
    return res.json()


def test_create_defaults_to_saved_and_round_trips_fields(client):
    pid = _profile()
    app = _create(
        client, pid, url="https://jobs.example.com/1", deadline="2026-11-30", keyword_match=75.0,
        evidence_match=52.5, description="Build APIs", notes="Ask about the team",
    )  # fmt: skip
    assert app["status"] == "saved" and app["applied_at"] is None
    assert app["deadline"] == "2026-11-30" and app["keyword_match"] == 75.0
    assert app["profile_id"] == pid and app["created_at"].endswith("Z")
    listed = client.get("/v1/applications", params={"profile_id": pid}).json()
    assert listed == [app]


def test_create_as_applied_stamps_applied_at(client):
    app = _create(client, _profile(), status="applied")
    assert app["status"] == "applied" and app["applied_at"] is not None


def test_list_is_newest_first_and_per_profile(client):
    pid, other = _profile(), _profile("Someone Else")
    first = _create(client, pid, company="A")
    second = _create(client, pid, company="B")
    _create(client, other, company="C")
    ids = [a["id"] for a in client.get("/v1/applications", params={"profile_id": pid}).json()]
    assert ids == [second["id"], first["id"]]


def test_update_changes_only_the_given_fields(client):
    app = _create(client, _profile(), deadline="2026-11-30", notes="keep")
    res = client.patch(f"/v1/applications/{app['id']}", json={"status": "interviewing"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "interviewing" and body["notes"] == "keep" and body["deadline"] == "2026-11-30"
    assert body["updated_at"] >= app["updated_at"]


def test_update_to_applied_stamps_once_and_keeps_explicit_time(client):
    app = _create(client, _profile())
    stamped = client.patch(f"/v1/applications/{app['id']}", json={"status": "applied"}).json()
    assert stamped["applied_at"] is not None
    again = client.patch(f"/v1/applications/{app['id']}", json={"status": "offer"}).json()
    assert again["applied_at"] == stamped["applied_at"]

    other = _create(client, _profile())
    given = "2026-10-01T09:30:00Z"
    res = client.patch(f"/v1/applications/{other['id']}", json={"status": "applied", "applied_at": given})
    assert res.json()["applied_at"] == given


def test_update_can_clear_deadline_and_notes(client):
    app = _create(client, _profile(), deadline="2026-11-30", notes="x")
    body = client.patch(f"/v1/applications/{app['id']}", json={"deadline": None, "notes": None}).json()
    assert body["deadline"] is None and body["notes"] is None


def test_update_rejects_unknown_status(client):
    app = _create(client, _profile())
    res = client.patch(f"/v1/applications/{app['id']}", json={"status": "ghosted"})
    assert res.status_code == 422
    assert_error_shape(res.json())


def test_delete_then_gone(client):
    app = _create(client, _profile())
    assert client.delete(f"/v1/applications/{app['id']}").status_code == 204
    assert client.patch(f"/v1/applications/{app['id']}", json={"notes": "x"}).status_code == 404
    assert client.delete(f"/v1/applications/{app['id']}").status_code == 404


def test_unknown_ids_are_404_with_the_error_shape(client):
    missing = str(uuid4())
    for res in (
        client.get("/v1/applications", params={"profile_id": missing}),
        client.post("/v1/applications", json={"profile_id": missing, "company": "A", "title": "B"}),
        client.patch(f"/v1/applications/{missing}", json={"notes": "x"}),
        client.delete(f"/v1/applications/{missing}"),
    ):
        assert res.status_code == 404
        assert_error_shape(res.json())


def test_deleting_the_profile_removes_its_applications(client):
    pid = _profile()
    _create(client, pid)
    assert client.delete(f"/v1/profiles/{pid}").status_code == 204
    with SessionLocal() as db:
        assert db.query(models.Application).count() == 0
