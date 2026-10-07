import logging
import time
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.config import Settings
from app.db.base import SessionLocal
from app.db.models import CacheEntry
from app.errors import ApiError
from app.services.github import GitHubClient, collect, request_fingerprint

TOKEN = "ghp_TESTTOKEN_do_not_log_1234567890"
QUERY = "query { viewer { login } }"
OK = {"data": {"viewer": {"login": "someone"}}}


class Script:
    """A transport replaying a fixed sequence of responses or exceptions, recording the calls."""

    def __init__(self, *items):
        self.items = list(items)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self.items.pop(0) if len(self.items) > 1 else self.items[0]
        if isinstance(item, Exception):
            raise item
        status, body, headers = (item + ({},))[:3] if isinstance(item, tuple) else (200, item, {})
        return httpx.Response(status, json=body, headers=headers)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


def make_client(db, script: Script, waits: list[float] | None = None, token: str = TOKEN) -> GitHubClient:
    waits = waits if waits is not None else []
    return GitHubClient(
        db,
        Settings(_env_file=None, github_token=token),
        transport=httpx.MockTransport(script),
        sleep=waits.append,
    )


def error_of(call) -> ApiError:
    with pytest.raises(ApiError) as exc:
        call()
    return exc.value


def test_no_token_is_github_not_configured(db):
    err = error_of(lambda: GitHubClient(db, Settings(_env_file=None, github_token="")))
    assert (err.status_code, err.code) == (503, "github_not_configured")


@pytest.mark.parametrize("login", ["", "-bad", "has space", "a" * 40, "semi;colon", "under_score"])
def test_invalid_usernames_never_reach_github(db, login):
    script = Script(OK)
    err = error_of(lambda: collect(login, db, client=make_client(db, script)))
    assert (err.status_code, err.code) == (404, "github_not_found")
    assert script.requests == []


def test_unknown_user_is_404_and_not_cached(db):
    payload = {"data": {"user": None}, "errors": [{"type": "NOT_FOUND", "message": "Could not resolve"}]}
    client = make_client(db, Script(payload))
    err = error_of(lambda: collect("nobody-here", db, client=client))
    assert (err.status_code, err.code) == (404, "github_not_found")
    assert db.query(CacheEntry).count() == 0


def test_requests_carry_the_token_and_api_version(db):
    script = Script(OK)
    make_client(db, script).graphql(QUERY, {})
    headers = script.requests[0].headers
    assert headers["authorization"] == f"Bearer {TOKEN}"
    assert headers["x-github-api-version"] == "2022-11-28"


def test_primary_rate_limit_reports_when_to_retry(db):
    reset = str(int(time.time()) + 120)
    script = Script(
        (
            403,
            {"message": "API rate limit exceeded"},
            {"x-ratelimit-remaining": "0", "x-ratelimit-reset": reset},
        )
    )
    err = error_of(lambda: make_client(db, script).rest_get("/x"))
    assert (err.status_code, err.code) == (429, "rate_limited")
    assert 100 <= err.details["retry_after_s"] <= 125


def test_secondary_rate_limit_uses_retry_after(db):
    script = Script((403, {"message": "You have exceeded a secondary rate limit."}, {"retry-after": "30"}))
    err = error_of(lambda: make_client(db, script).rest_get("/x"))
    assert (err.status_code, err.code, err.details) == (429, "rate_limited", {"retry_after_s": 30})


def test_graphql_rate_limited_error(db):
    script = Script(
        {"data": None, "errors": [{"type": "RATE_LIMITED", "message": "API rate limit exceeded"}]}
    )
    err = error_of(lambda: make_client(db, script).graphql(QUERY, {}))
    assert (err.status_code, err.code) == (429, "rate_limited")
    assert db.query(CacheEntry).count() == 0


def test_bad_token_is_github_auth_failed(db):
    err = error_of(lambda: make_client(db, Script((401, {"message": "Bad credentials"}))).graphql(QUERY, {}))
    assert (err.status_code, err.code) == (503, "github_auth_failed")


def test_forbidden_without_rate_limit_is_unavailable_not_rate_limited(db):
    err = error_of(
        lambda: make_client(db, Script((403, {"message": "Repository access blocked"}))).rest_get("/x")
    )
    assert (err.status_code, err.code) == (502, "github_unavailable")


def test_server_errors_are_retried_twice_then_reported(db):
    waits: list[float] = []
    script = Script((502, {"message": "bad gateway"}))
    err = error_of(lambda: make_client(db, script, waits).graphql(QUERY, {}))
    assert (err.status_code, err.code) == (502, "github_unavailable")
    assert waits == [1.0, 2.0] and len(script.requests) == 3
    assert db.query(CacheEntry).count() == 0


def test_a_server_error_followed_by_success_recovers(db):
    waits: list[float] = []
    client = make_client(db, Script((503, {"message": "x"}), OK), waits)
    assert client.graphql(QUERY, {}) == OK["data"]
    assert waits == [1.0]


def test_timeouts_are_retried_then_reported(db):
    waits: list[float] = []
    script = Script(httpx.ReadTimeout("slow"))
    err = error_of(lambda: make_client(db, script, waits).graphql(QUERY, {}))
    assert (err.status_code, err.code) == (502, "github_unavailable")
    assert waits == [1.0, 2.0] and len(script.requests) == 3


def test_202_is_retried_with_backoff_until_ready(db):
    waits: list[float] = []
    script = Script((202, {}), (202, {}), (200, [{"week": 1}]))
    assert make_client(db, script, waits).rest_get("/repos/o/r/stats/commit_activity") == [{"week": 1}]
    assert waits == [1.0, 2.0] and len(script.requests) == 3


def test_202_forever_gives_up(db):
    waits: list[float] = []
    err = error_of(lambda: make_client(db, Script((202, {})), waits).rest_get("/x"))
    assert (err.status_code, err.code) == (502, "github_unavailable")
    assert waits == [1.0, 2.0, 4.0]


def test_missing_rest_resources(db):
    client = make_client(db, Script((404, {"message": "Not Found"})))
    assert client.rest_get("/repos/o/empty/git/trees/HEAD", missing_ok=True) is None
    err = error_of(lambda: make_client(db, Script((404, {"message": "Not Found"}))).rest_get("/repos/o/gone"))
    assert (err.status_code, err.code) == (404, "github_not_found")
    assert (
        make_client(db, Script((409, {"message": "Git Repository is empty."}))).rest_get(
            "/x", missing_ok=True
        )
        is None
    )
    assert db.query(CacheEntry).count() == 0


def test_responses_are_cached_for_24_hours(db):
    script = Script(OK)
    client = make_client(db, script)
    first = client.graphql(QUERY, {"a": 1})
    second = client.graphql(QUERY, {"a": 1})
    assert first == second and len(script.requests) == 1
    entry = db.query(CacheEntry).one()
    assert entry.kind == "github" and entry.key == request_fingerprint(
        "POST", "https://api.github.com/graphql", {"query": QUERY, "variables": {"a": 1}}
    )
    assert timedelta(hours=23, minutes=59) < entry.expires_at - datetime.now(UTC) <= timedelta(hours=24)

    client.graphql(QUERY, {"a": 2})  # different variables, different key
    assert len(script.requests) == 2

    entry.expires_at = datetime.now(UTC) - timedelta(seconds=1)  # expired: fetched again
    db.commit()
    client.graphql(QUERY, {"a": 1})
    assert len(script.requests) == 3


def test_token_never_reaches_logs_or_cache(db, caplog):
    caplog.set_level(logging.DEBUG)
    client = make_client(db, Script(OK))
    client.graphql(QUERY, {})
    error_of(lambda: make_client(db, Script((401, {"message": "Bad credentials"}))).graphql(QUERY, {"x": 1}))
    assert TOKEN not in caplog.text
    assert all(TOKEN not in str(e.value) for e in db.query(CacheEntry))
    assert "github graphql ok" in caplog.text
