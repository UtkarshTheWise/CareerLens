import logging

import httpx
import pytest
from pydantic import BaseModel, Field

from app.config import Settings
from app.db.base import SessionLocal
from app.db.models import CacheEntry
from app.schemas.llm import ResumeProfile
from app.services import llm
from app.services.llm import (
    GeminiProvider,
    GroqProvider,
    LLMError,
    OllamaProvider,
    ProviderUnavailable,
    build_providers,
    generate_structured,
    inline_refs,
    to_strict_schema,
)

SYSTEM = "You judge one project."
USER = "SECRET-PROMPT-TEXT about a project"
GOOD = '{"verdict": "specific", "score": 2}'


class Verdict(BaseModel):
    verdict: str
    score: int = Field(ge=0, le=3)


class FakeProvider:
    """Replays a script: each item is raw JSON text to return or an exception to raise."""

    def __init__(self, name: str, *script):
        self.name = name
        self.script = list(script)
        self.calls: list[dict] = []

    def model_for(self, tier):
        return f"{self.name}-{tier}"

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


def ask(db, *providers, **kwargs):
    return generate_structured(Verdict, SYSTEM, USER, db=db, providers=list(providers), **kwargs)


def test_primary_provider_answers(db):
    gemini, groq = FakeProvider("gemini", GOOD), FakeProvider("groq")
    assert ask(db, gemini, groq, tier="smart") == Verdict(verdict="specific", score=2)
    assert len(gemini.calls) == 1 and groq.calls == []
    call = gemini.calls[0]
    assert (call["model"], call["system"], call["user"], call["schema"]) == (
        "gemini-smart",
        SYSTEM,
        USER,
        Verdict,
    )
    assert call["timeout"] == 60.0


@pytest.mark.parametrize("reason", ["HTTP 429", "HTTP 503", "ReadTimeout"])
def test_falls_back_when_a_provider_is_unavailable(db, reason):
    gemini = FakeProvider("gemini", ProviderUnavailable(reason))
    groq = FakeProvider("groq", GOOD)
    assert ask(db, gemini, groq).score == 2
    assert len(gemini.calls) == 1 and len(groq.calls) == 1


def test_falls_through_the_whole_chain_to_ollama(db):
    chain = [
        FakeProvider("gemini", ProviderUnavailable("429")),
        FakeProvider("groq", ProviderUnavailable("429")),
        FakeProvider("ollama", GOOD),
    ]
    assert ask(db, *chain).verdict == "specific"


def test_all_providers_down_raises_llm_unavailable(db):
    with pytest.raises(LLMError) as exc:
        ask(
            db,
            FakeProvider("gemini", ProviderUnavailable("429")),
            FakeProvider("groq", ProviderUnavailable("500")),
        )
    assert exc.value.code == "llm_unavailable"
    assert db.query(CacheEntry).count() == 0


def test_rejected_request_is_not_hidden_by_a_fallback(db):
    gemini = FakeProvider("gemini", LLMError("llm_request_rejected", "HTTP 400"))
    groq = FakeProvider("groq", GOOD)
    with pytest.raises(LLMError) as exc:
        ask(db, gemini, groq)
    assert exc.value.code == "llm_request_rejected" and groq.calls == []


def test_no_provider_configured(db):
    with pytest.raises(LLMError) as exc:
        ask(db)
    assert exc.value.code == "llm_not_configured"


def test_second_identical_call_is_a_cache_hit(db):
    first = FakeProvider("gemini", GOOD)
    assert ask(db, first).score == 2
    second = FakeProvider("gemini")  # empty script: any call would fail
    assert ask(db, second).score == 2
    assert second.calls == []
    entry = db.query(CacheEntry).one()
    assert entry.kind == "llm" and len(entry.key) == 64 and entry.value == {"verdict": "specific", "score": 2}


def test_cache_is_shared_across_fallback_and_respects_inputs(db):
    ask(db, FakeProvider("gemini", ProviderUnavailable("429")), FakeProvider("groq", GOOD))
    assert ask(db, FakeProvider("gemini")).score == 2  # answer came from groq, still served

    other = FakeProvider("gemini", '{"verdict": "vague", "score": 0}')
    result = generate_structured(Verdict, SYSTEM, USER + " changed", db=db, providers=[other])
    assert result.verdict == "vague" and len(other.calls) == 1
    smart = FakeProvider("gemini", GOOD)
    ask(db, smart, tier="smart")  # a different tier is a different key
    assert len(smart.calls) == 1


def test_force_refresh_bypasses_and_overwrites_the_cache(db):
    ask(db, FakeProvider("gemini", GOOD))
    fresh = FakeProvider("gemini", '{"verdict": "vague", "score": 1}')
    assert ask(db, fresh, force_refresh=True).verdict == "vague"
    assert ask(db, FakeProvider("gemini")).verdict == "vague"
    assert db.query(CacheEntry).count() == 1


def test_invalid_reply_gets_exactly_one_retry_with_the_error(db):
    gemini = FakeProvider("gemini", '{"verdict": "specific", "score": 9, "leak": "MODEL-VALUE"}', GOOD)
    assert ask(db, gemini).score == 2
    assert len(gemini.calls) == 2
    retry_prompt = gemini.calls[1]["user"]
    assert retry_prompt.startswith(USER)
    assert "score: Input should be less than or equal to 3" in retry_prompt
    assert "MODEL-VALUE" not in retry_prompt and "9" not in retry_prompt.replace(USER, "")


def test_non_json_reply_is_also_retried(db):
    gemini = FakeProvider("gemini", "Sure! Here is the JSON you asked for", GOOD)
    assert ask(db, gemini).score == 2


def test_invalid_twice_raises_and_caches_nothing(db):
    gemini = FakeProvider("gemini", "{}", '{"verdict": 1}')
    groq = FakeProvider("groq", GOOD)
    with pytest.raises(LLMError) as exc:
        ask(db, gemini, groq)
    assert exc.value.code == "llm_invalid_response"
    assert len(gemini.calls) == 2 and groq.calls == []
    assert db.query(CacheEntry).count() == 0


def test_unavailable_during_retry_moves_to_next_provider(db):
    gemini = FakeProvider("gemini", "{}", ProviderUnavailable("429"))
    groq = FakeProvider("groq", GOOD)
    assert ask(db, gemini, groq).score == 2


def test_logs_never_contain_prompt_or_response(db, caplog):
    caplog.set_level(logging.DEBUG)
    ask(db, FakeProvider("gemini", ProviderUnavailable("HTTP 429")), FakeProvider("groq", "{}", GOOD))
    ask(db, FakeProvider("gemini"))
    text = caplog.text
    assert "provider=groq" in text and "outcome=ok" in text and "outcome=cache_hit" in text
    assert "outcome=unavailable" in text and "latency_ms=" in text
    for secret in ("SECRET-PROMPT-TEXT", SYSTEM, "specific"):
        assert secret not in text


# ---------------------------------------------------------------- provider wiring (no network)


def _settings(**kwargs) -> Settings:
    return Settings(_env_file=None, **kwargs)


def test_build_providers_order_and_skipping():
    assert build_providers(_settings()) == []
    names = [
        p.name
        for p in build_providers(_settings(gemini_api_key="g", groq_api_key="q", ollama_url="http://x"))
    ]
    assert names == ["gemini", "groq", "ollama"]
    assert [p.name for p in build_providers(_settings(groq_api_key="q"))] == ["groq"]


def test_models_come_from_settings():
    s = _settings(
        gemini_api_key="g", groq_api_key="q", gemini_model_fast="fast-x", gemini_model_smart="smart-x"
    )
    gemini, groq = build_providers(s)
    assert (gemini.model_for("fast"), gemini.model_for("smart")) == ("fast-x", "smart-x")
    assert groq.model_for("fast") == groq.model_for("smart") == s.groq_model


def _complete(provider):
    return provider.complete(model="m", system=SYSTEM, user=USER, schema=Verdict, timeout=5)


@pytest.mark.parametrize(
    ("status", "expected"), [(429, ProviderUnavailable), (503, ProviderUnavailable), (400, LLMError)]
)
def test_gemini_error_mapping_and_request_shape(monkeypatch, status, expected):
    from google.genai import errors

    provider = GeminiProvider(_settings(gemini_api_key="test-key"))
    seen = {}

    def fake_generate(**kwargs):
        seen.update(kwargs)
        raise errors.APIError(status, {"error": {"message": "x", "status": "X"}})

    monkeypatch.setattr(provider._client.models, "generate_content", fake_generate)
    with pytest.raises(expected):
        _complete(provider)
    config = seen["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema["properties"].keys() == {"verdict", "score"}
    assert config.system_instruction == SYSTEM and seen["contents"] == USER
    assert config.temperature is None and config.top_p is None  # no sampling knobs


def test_gemini_timeout_is_unavailable(monkeypatch):
    provider = GeminiProvider(_settings(gemini_api_key="test-key"))

    def boom(**_):
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(provider._client.models, "generate_content", boom)
    with pytest.raises(ProviderUnavailable):
        _complete(provider)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (429, ProviderUnavailable),
        (500, ProviderUnavailable),
        (413, ProviderUnavailable),
        (400, LLMError),
        (401, LLMError),
    ],
)
def test_groq_error_mapping_and_strict_schema(monkeypatch, status, expected):
    import groq

    provider = GroqProvider(_settings(groq_api_key="test-key"))
    seen = {}

    def fake_create(**kwargs):
        seen.update(kwargs)
        response = httpx.Response(status, request=httpx.Request("POST", "https://api.groq.test"))
        raise provider._client._make_status_error("x", body=None, response=response)

    monkeypatch.setattr(provider._client.chat.completions, "create", fake_create)
    with pytest.raises(expected):
        _complete(provider)
    fmt = seen["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"]["additionalProperties"] is False
    assert "temperature" not in seen
    assert isinstance(groq.RateLimitError, type)


def test_groq_timeout_is_unavailable(monkeypatch):
    import groq

    provider = GroqProvider(_settings(groq_api_key="test-key"))

    def boom(**_):
        raise groq.APITimeoutError(request=httpx.Request("POST", "https://api.groq.test"))

    monkeypatch.setattr(provider._client.chat.completions, "create", boom)
    with pytest.raises(ProviderUnavailable):
        _complete(provider)


def test_ollama_request_and_failure(monkeypatch):
    provider = OllamaProvider(_settings(ollama_url="http://localhost:11434/", ollama_model="tiny"))
    seen = {}

    def fake_post(url, json, timeout):
        seen.update(url=url, json=json)
        return httpx.Response(200, json={"message": {"content": GOOD}}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    assert provider.complete(model="tiny", system=SYSTEM, user=USER, schema=Verdict, timeout=5) == GOOD
    assert seen["url"] == "http://localhost:11434/api/chat"
    assert seen["json"]["stream"] is False and seen["json"]["format"]["type"] == "object"

    def refused(*_, **__):
        raise httpx.ConnectError("no ollama here")

    monkeypatch.setattr(llm.httpx, "post", refused)
    with pytest.raises(ProviderUnavailable):
        _complete(provider)


# ---------------------------------------------------------------- schema helpers


def _walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def test_inline_refs_removes_refs_and_defs():
    schema = inline_refs(ResumeProfile.model_json_schema())
    assert "$defs" not in schema
    assert not any("$ref" in node for node in _walk(schema))
    assert schema["properties"]["education"]["items"]["properties"].keys() >= {"institution", "field"}


def test_strict_schema_for_resume_profile():
    schema = to_strict_schema(ResumeProfile.model_json_schema())
    objects = [n for n in _walk(schema) if n.get("type") == "object"]
    assert len(objects) == 5  # ResumeProfile + education, experience, project, certification
    for obj in objects:
        assert obj["additionalProperties"] is False
        assert obj["required"] == list(obj["properties"])
    assert not any("$ref" in n or "default" in n for n in _walk(schema) if "properties" not in n)
    # a property that happens to be called like a keyword survives
    assert "field" in schema["properties"]["education"]["items"]["properties"]
