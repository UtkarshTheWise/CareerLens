import time

import jwt
import pytest

from app import rate_limit
from app.config import Settings, get_settings
from app.main import app
from tests.conftest import assert_error_shape

SECRET = "rate-limit-secret-rate-limit-secret-32"


@pytest.fixture(autouse=True)
def _fresh_limits():
    rate_limit.reset()
    yield
    rate_limit.reset()
    rate_limit.clock = time.monotonic


def token(sub: str) -> dict:
    payload = {"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 600}
    return {"Authorization": "Bearer " + jwt.encode(payload, SECRET, "HS256")}


def secure(**limits) -> None:
    settings = Settings(_env_file=None, dev_auth=False, supabase_jwt_secret=SECRET, **limits)
    app.dependency_overrides[get_settings] = lambda: settings


def test_the_window_counts_only_the_last_hour():
    now = [1000.0]
    rate_limit.clock = lambda: now[0]
    for _ in range(3):
        rate_limit.check("quiz", "u1", 3)
    with pytest.raises(rate_limit.ApiError) as caught:
        rate_limit.check("quiz", "u1", 3)
    assert caught.value.status_code == 429 and caught.value.code == "rate_limited"
    assert 3590 <= caught.value.details["retry_after_s"] <= 3601
    now[0] += 3601
    rate_limit.check("quiz", "u1", 3)  # an hour later the old uses no longer count


def test_users_and_buckets_are_counted_separately_and_zero_means_off():
    rate_limit.check("quiz", "u1", 1)
    rate_limit.check("quiz", "u2", 1)
    rate_limit.check("analysis", "u1", 1)
    for _ in range(50):
        rate_limit.check("quiz", "u3", 0)


def test_the_dev_auth_user_is_never_limited():
    for _ in range(50):
        rate_limit.check("quiz", "dev", 1)


def test_an_expensive_route_returns_429_in_the_error_shape_after_the_limit(client):
    secure(rate_limit_match_per_hour=2)
    body = {
        "profile_id": "00000000-0000-4000-8000-000000000000",
        "posting": {"title": "t", "description": "d", "source": "manual"},
    }
    first = [client.post("/v1/jobs/match", json=body, headers=token("u1")).status_code for _ in range(2)]
    assert first == [404, 404]  # counted, then refused by the route itself (unknown profile)
    limited = client.post("/v1/jobs/match", json=body, headers=token("u1"))
    assert limited.status_code == 429 and limited.json()["code"] == "rate_limited"
    assert_error_shape(limited.json())
    assert (
        client.post("/v1/jobs/match", json=body, headers=token("u2")).status_code == 404
    )  # others unaffected
