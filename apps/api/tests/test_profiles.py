from pathlib import Path
from uuid import uuid4

from app.config import Settings, get_settings
from app.db import models
from app.db.base import SessionLocal
from app.main import app
from app.services.ingest import MAX_UPLOAD_BYTES
from tests.conftest import assert_error_shape

FIXTURES = Path(__file__).parent / "fixtures"


def _create(client, **overrides) -> dict:
    body = {"name": "Priya Raman", "github_username": "careerlens-demo", "target_role_id": "sde-backend"}
    res = client.post("/v1/profiles", json={**body, **overrides})
    assert res.status_code == 201, res.text
    return res.json()


def _upload(client, profile_id: str, name: str, kind: str = "resume", data: bytes | None = None):
    data = data if data is not None else (FIXTURES / name).read_bytes()
    return client.post(
        f"/v1/profiles/{profile_id}/documents", data={"kind": kind}, files={"file": (name, data)}
    )


def test_create_get_patch_delete(client):
    created = _create(client, portfolio_urls=["https://example.com/case-study"])
    assert created["has_resume"] is False and created["latest_analysis_id"] is None
    pid = created["id"]

    assert client.get(f"/v1/profiles/{pid}").json() == created

    patched = client.patch(f"/v1/profiles/{pid}", json={"department": "CSE", "github_username": None})
    assert patched.status_code == 200
    assert patched.json()["department"] == "CSE"
    assert patched.json()["github_username"] is None
    assert patched.json()["name"] == "Priya Raman"  # untouched fields stay
    assert patched.json()["portfolio_urls"] == ["https://example.com/case-study"]

    assert client.delete(f"/v1/profiles/{pid}").status_code == 204
    gone = client.get(f"/v1/profiles/{pid}")
    assert gone.status_code == 404
    assert_error_shape(gone.json())


def test_create_requires_name_and_known_role(client):
    missing = client.post("/v1/profiles", json={})
    assert missing.status_code == 422
    assert_error_shape(missing.json())

    bad_role = client.post("/v1/profiles", json={"name": "A B", "target_role_id": "astronaut"})
    assert bad_role.status_code == 422
    assert bad_role.json()["details"] == {"field": "target_role_id"}

    bad_cohort = client.post("/v1/profiles", json={"name": "A B", "cohort_id": str(uuid4())})
    assert bad_cohort.status_code == 422


def test_patch_validates_and_unknown_profile_is_404(client):
    pid = _create(client)["id"]
    assert client.patch(f"/v1/profiles/{pid}", json={"target_role_id": "astronaut"}).status_code == 422
    assert client.patch(f"/v1/profiles/{pid}", json={"name": None}).status_code == 422
    assert client.patch(f"/v1/profiles/{uuid4()}", json={"department": "IT"}).status_code == 404
    assert client.get("/v1/profiles/not-a-uuid").status_code == 422


def test_upload_resume_pdf_and_docx(client):
    pid = _create(client)["id"]
    res = _upload(client, pid, "resume.pdf")
    assert res.status_code == 200
    assert res.json()["has_resume"] is True and res.json()["has_linkedin"] is False

    # a second resume replaces the first; text is stored raw, server-side only
    assert _upload(client, pid, "resume.docx").status_code == 200
    with SessionLocal() as db:
        docs = db.query(models.Document).filter_by(profile_id=pid).all()
        assert [(d.kind, d.filename, d.page_count) for d in docs] == [("resume", "resume.docx", None)]
        assert "Aarav Mehta" in docs[0].text
    assert "Aarav" not in res.text  # the profile response never carries document text


def test_upload_plain_text_resume_built_in_the_app(client):
    pid = _create(client)["id"]
    text = "Asha Verma\nasha@example.com\n\nSKILLS\nPython, SQL\n\nPROJECTS\nCampus API: hostel requests\n"
    res = _upload(client, pid, "resume.txt", data=text.encode())
    assert res.status_code == 200 and res.json()["has_resume"] is True
    with SessionLocal() as db:
        doc = db.query(models.Document).filter_by(profile_id=pid).one()
        assert (doc.kind, doc.filename, doc.page_count) == ("resume", "resume.txt", None)
        assert doc.text == text
    assert "Asha" not in res.text  # document text never appears in the profile response


def test_upload_linkedin_and_pasted_text_both_count(client):
    pid = _create(client)["id"]
    assert _upload(client, pid, "resume.pdf", kind="linkedin").json()["has_linkedin"] is True
    other = _create(client, linkedin_text="Backend intern at Northwind Labs")
    assert other["has_linkedin"] is True and other["has_resume"] is False


def test_upload_errors_use_the_contract_shape(client):
    pid = _create(client)["id"]
    cases = [
        (_upload(client, pid, "notes.txt", data=bytes(range(32)) * 4), 422, "unsupported_file"),
        (_upload(client, pid, "notes", data=b"plain text without a .txt name " * 3), 422, "unsupported_file"),
        (_upload(client, pid, "notes.txt", data=b"too short"), 422, "no_text_extracted"),
        (_upload(client, pid, "no_text.pdf"), 422, "no_text_extracted"),
        (_upload(client, pid, "big.pdf", data=b"%PDF-" + b"0" * MAX_UPLOAD_BYTES), 413, "payload_too_large"),
        (_upload(client, pid, "resume.pdf", kind="passport"), 422, "validation_error"),
        (_upload(client, str(uuid4()), "resume.pdf"), 404, "not_found"),
    ]
    for res, status, code in cases:
        assert (res.status_code, res.json()["code"]) == (status, code)
        assert_error_shape(res.json())
    assert client.get(f"/v1/profiles/{pid}").json()["has_resume"] is False


def test_delete_removes_documents_too(client):
    pid = _create(client)["id"]
    _upload(client, pid, "resume.pdf")
    assert client.delete(f"/v1/profiles/{pid}").status_code == 204
    with SessionLocal() as db:
        assert db.query(models.Document).count() == 0


def test_profiles_are_private_without_dev_auth(client):
    pid = _create(client)["id"]
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, dev_auth=False)
    for res in (
        client.get(f"/v1/profiles/{pid}"),
        client.get(f"/v1/profiles/{pid}", headers={"Authorization": "Bearer someone-else"}),
        client.post("/v1/profiles", json={"name": "A B"}),
    ):
        assert res.status_code == 401
        assert_error_shape(res.json())
