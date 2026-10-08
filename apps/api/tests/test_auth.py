import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.config import Settings, check_settings, get_settings
from app.db import models
from app.db.base import SessionLocal
from app.main import app
from app.services import auth
from tests.conftest import assert_error_shape

SECRET = "test-secret-test-secret-test-secret-32"
URL = "https://proj.supabase.co"


def settings(**kw) -> Settings:
    base = {"dev_auth": False, "supabase_jwt_secret": SECRET}
    return Settings(_env_file=None, **{**base, **kw})


def token(sub="user-a", key=SECRET, alg="HS256", **claims) -> str:
    payload = {"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 600, **claims}
    payload = {k: v for k, v in payload.items() if v is not None}
    return jwt.encode(payload, key, algorithm=alg)


def use(**kw) -> None:
    s = settings(**kw)
    app.dependency_overrides[get_settings] = lambda: s


def bearer(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(autouse=True)
def _secure(client):
    use()


# ---------------------------------------------------------------- token checks


def test_a_valid_token_reaches_the_api(client):
    res = client.get("/v1/roles", headers=bearer(token()))
    assert res.status_code == 200 and len(res.json()) == 7


def test_no_token_or_wrong_scheme_is_401(client):
    for headers in ({}, {"Authorization": "Basic abc"}, {"Authorization": "Bearer"}):
        res = client.get("/v1/roles", headers=headers)
        assert res.status_code == 401 and res.json()["code"] == "unauthorized"
        assert_error_shape(res.json())


@pytest.mark.parametrize(
    "bad",
    [
        token(exp=int(time.time()) - 10),  # expired
        token(aud="someone-else"),
        token(key="another-secret-another-secret-another-1"),  # wrong signature
        token(sub=None),  # no subject
        token(exp=None),  # no expiry
        "not-a-jwt",
        "a.b.c",
        jwt.encode(
            {"sub": "x", "aud": "authenticated", "exp": int(time.time()) + 600}, None, algorithm="none"
        ),
    ],
)
def test_bad_tokens_are_a_generic_401(client, bad):
    res = client.get("/v1/roles", headers=bearer(bad))
    assert res.status_code == 401
    assert res.json() == {
        "code": "unauthorized", "message": "Invalid or expired sign-in. Please sign in again.", "details": None,
    }  # fmt: skip
    assert bad not in res.text


def test_an_hs256_token_is_refused_when_no_secret_is_configured(client):
    use(supabase_jwt_secret="", supabase_url=URL)
    assert client.get("/v1/roles", headers=bearer(token())).status_code == 401


def test_the_issuer_is_checked_when_the_project_url_is_known(client):
    use(supabase_url=URL)
    assert client.get("/v1/roles", headers=bearer(token(iss=f"{URL}/auth/v1"))).status_code == 200
    assert (
        client.get("/v1/roles", headers=bearer(token(iss="https://evil.example/auth/v1"))).status_code == 401
    )
    assert client.get("/v1/roles", headers=bearer(token())).status_code == 401  # no issuer at all


def test_asymmetric_tokens_are_checked_against_the_projects_published_keys(client, monkeypatch):
    private = ec.generate_private_key(ec.SECP256R1())
    keys = SimpleNamespace(get_signing_key_from_jwt=lambda tok: SimpleNamespace(key=private.public_key()))
    monkeypatch.setattr(auth, "jwks_client_for", lambda url: keys)
    use(supabase_jwt_secret="", supabase_url=URL)
    good = token(key=private, alg="ES256", iss=f"{URL}/auth/v1")
    assert client.get("/v1/roles", headers=bearer(good)).status_code == 200
    other = ec.generate_private_key(ec.SECP256R1())
    forged = token(key=other, alg="ES256", iss=f"{URL}/auth/v1")
    assert client.get("/v1/roles", headers=bearer(forged)).status_code == 401


def test_an_asymmetric_token_without_a_project_url_is_refused(client):
    private = ec.generate_private_key(ec.SECP256R1())
    res = client.get("/v1/roles", headers=bearer(token(key=private, alg="ES256")))
    assert res.status_code == 401


def test_the_token_never_reaches_the_logs(client, caplog):
    caplog.set_level("DEBUG")
    bad = token(key="another-secret-another-secret-another-1")
    client.get("/v1/roles", headers=bearer(bad))
    assert bad not in caplog.text and "Bearer" not in caplog.text


# ---------------------------------------------------------------- each user sees only their own data


def make_profile(client, tok: str) -> str:
    res = client.post("/v1/profiles", json={"name": "Priya Raman"}, headers=bearer(tok))
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_me_needs_a_profile_then_returns_it(client):
    tok = token("user-a")
    assert client.get("/v1/me", headers=bearer(tok)).status_code == 404
    pid = make_profile(client, tok)
    assert client.get("/v1/me", headers=bearer(tok)).json()["id"] == pid
    again = client.post("/v1/profiles", json={"name": "Second"}, headers=bearer(tok))
    assert again.status_code == 409  # one profile per account


def test_a_user_cannot_reach_another_users_data(client):
    a, b = token("user-a"), token("user-b")
    pid = make_profile(client, a)
    with SessionLocal() as db:
        analysis = models.Analysis(profile_id=pid, role_id="sde-backend", status="done", progress=100)
        db.add(analysis)
        db.flush()
        quiz = models.Quiz(
            analysis_id=analysis.id, profile_id=pid, project_id="p", project_title="p", mode="practice"
        )
        application = models.Application(profile_id=pid, company="C", title="T")
        db.add_all([quiz, application])
        db.commit()
        ids = {"analysis": analysis.id, "quiz": quiz.id, "application": application.id}
    mine = [
        f"/v1/profiles/{pid}", f"/v1/profiles/{pid}/analyses", f"/v1/analyses/{ids['analysis']}",
        f"/v1/quizzes/{ids['quiz']}", f"/v1/profiles/{pid}/quizzes",
    ]  # fmt: skip
    for path in mine:
        assert client.get(path, headers=bearer(a)).status_code == 200, path
        theirs = client.get(path, headers=bearer(b))
        assert theirs.status_code == 404, path
        assert_error_shape(theirs.json())
    assert client.get("/v1/applications", params={"profile_id": pid}, headers=bearer(b)).status_code == 404
    assert (
        client.patch(
            f"/v1/applications/{ids['application']}", json={"notes": "x"}, headers=bearer(b)
        ).status_code
        == 404
    )
    assert client.delete(f"/v1/profiles/{pid}", headers=bearer(b)).status_code == 404
    assert client.delete(f"/v1/profiles/{pid}", headers=bearer(a)).status_code == 204


# ---------------------------------------------------------------- placement staff


@pytest.fixture
def cohort_id():
    with SessionLocal() as db:
        cohort = models.Cohort(name="B.Tech CSE 2027")
        db.add(cohort)
        db.commit()
        return cohort.id


def cohort_routes(cid: str) -> list[str]:
    q = "?role_id=sde-backend"
    return [
        "/v1/cohorts",
        f"/v1/cohorts/{cid}/insights{q}",
        f"/v1/cohorts/{cid}/students{q}",
        f"/v1/cohorts/{cid}/export{q}",
    ]


def test_students_cannot_read_cohort_data(client, cohort_id):
    for path in cohort_routes(cohort_id):
        res = client.get(path, headers=bearer(token("student-1", email="student@college.edu")))
        assert res.status_code == 403, path
        assert res.json()["code"] == "forbidden"
        assert_error_shape(res.json())
        assert client.get(path).status_code == 401  # and anonymous is 401, not 403


def test_staff_by_the_allow_list_email_or_user_id(client, cohort_id):
    use(placement_staff="Coordinator@College.edu, staff-uuid-7")
    by_email = bearer(token("someone", email="coordinator@college.edu"))
    by_id = bearer(token("staff-uuid-7"))
    for headers in (by_email, by_id):
        for path in cohort_routes(cohort_id):
            assert client.get(path, headers=headers).status_code == 200, path
    assert client.get("/v1/cohorts", headers=bearer(token("other", email="x@college.edu"))).status_code == 403


def test_staff_by_the_role_claim_and_not_by_a_user_editable_field(client, cohort_id):
    assert (
        client.get("/v1/cohorts", headers=bearer(token("t", app_metadata={"role": "placement"}))).status_code
        == 200
    )
    assert (
        client.get("/v1/cohorts", headers=bearer(token("t", app_metadata={"role": "student"}))).status_code
        == 403
    )
    # user_metadata can be edited by the user themselves: it must never grant access
    assert (
        client.get("/v1/cohorts", headers=bearer(token("t", user_metadata={"role": "placement"}))).status_code
        == 403
    )


def test_dev_auth_sees_everything(client, cohort_id):
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, dev_auth=True)
    for path in cohort_routes(cohort_id):
        assert client.get(path).status_code == 200, path


# ---------------------------------------------------------------- production guard


def test_production_refuses_dev_auth():
    with pytest.raises(RuntimeError, match="DEV_AUTH"):
        check_settings(
            Settings(_env_file=None, environment="production", dev_auth=True, supabase_jwt_secret="x")
        )


def test_production_needs_a_way_to_verify_tokens():
    with pytest.raises(RuntimeError, match="SUPABASE_JWT_SECRET"):
        check_settings(Settings(_env_file=None, environment="production", dev_auth=False))


def test_production_accepts_either_key_source_and_development_accepts_anything():
    check_settings(
        Settings(_env_file=None, environment="production", dev_auth=False, supabase_jwt_secret="x")
    )
    check_settings(Settings(_env_file=None, environment="production", dev_auth=False, supabase_url=URL))
    check_settings(Settings(_env_file=None, environment="development", dev_auth=True))
    check_settings(
        Settings(_env_file=None, environment="Production ", dev_auth=False, supabase_jwt_secret="x")
    )
