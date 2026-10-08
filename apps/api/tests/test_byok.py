"""Bring your own key: validation, that the student's provider is the only one used, and that the key is
never kept or logged."""

import logging

import pytest

from app import rate_limit
from app.config import Settings
from app.errors import ApiError
from app.main import app
from app.routers.analyses import get_pipeline_deps
from app.routers.jobs import get_llm_providers
from app.services import byok
from app.services.llm import LLMError
from tests.llm_fakes import SchemaProvider
from tests.test_matching import _body, _profile, posting
from tests.test_rate_limit import secure, token

KEY = "AIzaSy-this-is-a-secret-user-key-0123456789"
HEADERS = {"X-LLM-Provider": "gemini", "X-LLM-Key": KEY}
SETTINGS = Settings(_env_file=None)


@pytest.fixture
def built(monkeypatch):
    made: list[tuple[str, str]] = []

    def fake(name, key, settings):
        made.append((name, key))
        return SchemaProvider({"JobPostingExtract": {"title": "x", "required_skills": ["Python"]}})

    monkeypatch.setattr(byok, "build_user_provider", fake)
    return made


def test_no_headers_means_the_shared_providers():
    assert byok.user_providers(None, None, SETTINGS) is None
    assert byok.user_providers("", "  ", SETTINGS) is None


@pytest.mark.parametrize(
    ("provider", "key"),
    [
        ("openai", KEY),  # not offered
        ("gemini", None),  # a provider without a key
        (None, KEY),  # a key without a provider
        ("gemini", "short"),
        ("groq", "has a space inside it, 20+ chars"),
        ("gemini", "k" * 201),
        ("gemini", "ключ-с-юникодом-0123456789"),
    ],
)
def test_a_malformed_pair_is_a_422_that_never_echoes_the_key(provider, key, built):
    with pytest.raises(ApiError) as caught:
        byok.user_providers(provider, key, SETTINGS)
    assert caught.value.status_code == 422 and caught.value.code == "invalid_llm_key"
    assert (key or "x") not in caught.value.message
    assert built == []


def test_a_good_pair_builds_exactly_one_provider(built):
    providers = byok.user_providers(" Groq ", f" {KEY} ", SETTINGS)
    assert len(providers) == 1 and built == [("groq", KEY)]


def test_real_providers_are_marked_as_the_students_own():
    provider = byok.build_user_provider("groq", "gsk_" + "a" * 40, SETTINGS)
    assert provider.name == "groq" and provider.user_key is True
    assert byok.build_user_provider("gemini", KEY, SETTINGS).user_key is True


def test_the_pipeline_deps_carry_only_the_students_provider(built):
    deps = get_pipeline_deps(byok.user_providers("gemini", KEY, SETTINGS))
    assert deps.providers is not None and len(deps.providers) == 1
    assert get_pipeline_deps(None).providers is None


def test_a_job_match_uses_the_students_key_and_not_the_shared_one(client, built):
    body = {"profile_id": _profile(), "posting": posting(source="llm").model_dump(mode="json")}
    res = client.post("/v1/jobs/match", json=body, headers=HEADERS)
    assert res.status_code == 200 and res.json()["keyword_match"] > 0
    assert built == [("gemini", KEY)]
    assert KEY not in res.text


def test_a_bad_header_pair_is_refused_before_any_work(client, built):
    res = client.post("/v1/jobs/match", json=_body(_profile()), headers={"X-LLM-Key": KEY})
    assert res.status_code == 422 and res.json()["code"] == "invalid_llm_key"
    assert KEY not in res.text


def test_a_rejected_key_is_a_clear_error_not_a_quiet_fallback(client):
    class Rejected(SchemaProvider):
        def complete(self, **kwargs):
            raise LLMError("llm_key_rejected", "Your Gemini key was rejected. Check it in Settings.")

    app.dependency_overrides[get_llm_providers] = lambda: [Rejected({})]
    body = {"profile_id": _profile(), "posting": posting(source="llm").model_dump(mode="json")}
    res = client.post("/v1/jobs/match", json=body)
    assert res.status_code == 400 and res.json()["code"] == "invalid_llm_key"
    assert "Settings" in res.json()["message"]


def test_a_user_key_skips_the_shared_rate_limit(client, built):
    rate_limit.reset()
    secure(rate_limit_match_per_hour=1)
    body = {
        "profile_id": "00000000-0000-4000-8000-000000000000",
        "posting": {"title": "t", "description": "d", "source": "manual"},
    }
    codes = [
        client.post("/v1/jobs/match", json=body, headers={**token("u1"), **HEADERS}).status_code
        for _ in range(3)
    ]
    assert codes == [404, 404, 404]  # never 429
    without = [client.post("/v1/jobs/match", json=body, headers=token("u2")).status_code for _ in range(2)]
    assert without == [404, 429]
    rate_limit.reset()


def test_the_key_never_reaches_the_logs(client, built, caplog):
    caplog.set_level(logging.DEBUG)
    body = {"profile_id": _profile(), "posting": posting(source="llm").model_dump(mode="json")}
    client.post("/v1/jobs/match", json=body, headers=HEADERS)
    client.post("/v1/jobs/match", json=body, headers={"X-LLM-Key": KEY})  # refused
    assert KEY not in caplog.text


def test_the_header_is_not_part_of_the_contract_schema(client):
    schema = client.get("/openapi.json").json()
    assert "x-llm-key" not in str(schema).lower()
