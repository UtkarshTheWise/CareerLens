from app.schemas.api import Profile
from tests.conftest import assert_error_shape


def test_me_returns_demo_profile_under_dev_auth(client):
    res = client.get("/v1/me")
    assert res.status_code == 200
    profile = Profile.model_validate(res.json())
    assert profile.name == "Demo Student"
    assert profile.has_resume is False
    assert profile.has_linkedin is False
    assert profile.latest_analysis_id is None


def test_me_is_stable_across_calls(client):
    first = client.get("/v1/me").json()
    second = client.get("/v1/me", headers={"Authorization": "Bearer anything"}).json()
    assert first["id"] == second["id"]


def test_me_requires_a_token_without_dev_auth(client, no_dev_auth):
    res = client.get("/v1/me")
    assert res.status_code == 401
    assert_error_shape(res.json())
    assert res.json()["code"] == "unauthorized"


def test_roles_require_a_token_without_dev_auth(client, no_dev_auth):
    assert client.get("/v1/roles").status_code == 401


def test_under_dev_auth_me_follows_the_profile_just_created(client):
    demo = client.get("/v1/me").json()
    created = client.post("/v1/profiles", json={"name": "New Student"}).json()
    assert client.get("/v1/me").json()["id"] == created["id"] != demo["id"]
    again = client.post("/v1/profiles", json={"name": "Another Student"}).json()
    assert client.get("/v1/me").json()["id"] == again["id"]
    assert client.get(f"/v1/profiles/{created['id']}").status_code == 200  # older profiles stay reachable
