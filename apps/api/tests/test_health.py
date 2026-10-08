import pytest

from app.config import API_VERSION
from app.db import base
from app.deps import get_db
from app.main import app
from app.services import llm
from tests.conftest import assert_error_shape
from tests.llm_fakes import SchemaProvider


@pytest.fixture(autouse=True)
def _reset_provider_state():
    llm._last_ok["provider"] = None
    yield
    llm._last_ok["provider"] = None


def test_health_reports_status_version_and_needs_no_sign_in(client, no_dev_auth):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok" and body["version"] == API_VERSION


def test_health_names_the_provider_that_last_answered(client):
    from pydantic import BaseModel

    class Verdict(BaseModel):
        ok: bool

    assert client.get("/health").json().get("llm_provider") in (
        None,
        "gemini",
        "groq",
        "ollama",
    )  # configured, if any
    provider = SchemaProvider({"Verdict": {"ok": True}})
    with base.SessionLocal() as db:
        llm.generate_structured(Verdict, "s", "u", db=db, providers=[provider])
    assert client.get("/health").json()["llm_provider"] == "fake"


def test_a_cached_answer_does_not_change_the_reported_provider(client):
    from pydantic import BaseModel

    class Verdict(BaseModel):
        ok: bool

    with base.SessionLocal() as db:
        llm.generate_structured(
            Verdict, "s", "u", db=db, providers=[SchemaProvider({"Verdict": {"ok": True}})]
        )
        llm._last_ok["provider"] = "groq"
        llm.generate_structured(Verdict, "s", "u", db=db, providers=[SchemaProvider({})])  # cache hit
    assert client.get("/health").json()["llm_provider"] == "groq"


def test_an_unreachable_database_is_a_503_in_the_error_shape(client):
    class Broken:
        def execute(self, *_):
            raise ConnectionError("db down at postgres://user:password@host/db")

        def close(self):
            pass

    app.dependency_overrides[get_db] = lambda: Broken()
    res = client.get("/health")
    assert res.status_code == 503 and res.json()["code"] == "db_unavailable"
    assert_error_shape(res.json())
    assert "password" not in res.text  # the driver's message is never echoed


# ---------------------------------------------------------------- database engine settings


def test_postgres_engines_get_timeouts_recycling_and_pooler_safe_settings(monkeypatch):
    seen = {}
    monkeypatch.setattr(base, "create_engine", lambda url, **kw: seen.update(url=url, **kw))
    base.make_engine("postgres://u:p@host/db", statement_timeout_ms=15000)
    assert seen["url"].startswith("postgresql+psycopg://") and seen["pool_pre_ping"] is True
    assert seen["pool_recycle"] == base.DB_POOL_RECYCLE_S == 300
    args = seen["connect_args"]
    assert args["connect_timeout"] == 10 and args["prepare_threshold"] is None
    assert args["options"] == "-c statement_timeout=15000"


def test_the_statement_timeout_option_is_only_sent_when_asked_for(monkeypatch):
    seen = {}
    monkeypatch.setattr(base, "create_engine", lambda url, **kw: seen.update(**kw))
    base.make_engine("postgresql://u:p@host/db")
    assert "options" not in seen["connect_args"]


def test_every_external_call_has_a_timeout_constant():
    from app.services import github, llm, portfolio

    assert github.TIMEOUT_S <= 30 and portfolio.TIMEOUT_S <= 15
    assert set(llm.TIMEOUT_S) == {"fast", "smart"} and max(llm.TIMEOUT_S.values()) <= 90


def test_a_missing_provider_is_left_out_not_null(client, monkeypatch):
    """The contract types llm_provider as a string: with no provider configured the key must be absent."""
    from app.config import Settings, get_settings

    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, dev_auth=True)
    assert "llm_provider" not in client.get("/health").json()
