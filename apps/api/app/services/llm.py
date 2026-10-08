"""The single LLM gateway (docs/PIPELINE.md "Design rules"). Every model call goes through
`generate_structured`: Gemini -> Groq -> Ollama, cached, validated with Pydantic, one retry
on a schema mismatch. No sampling knobs. Prompts and responses are never logged.
"""

import copy
import hashlib
import json
import logging
import time
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import CacheEntry

logger = logging.getLogger("careerlens.llm")

Tier = Literal["fast", "smart"]
TIMEOUT_S: dict[str, float] = {"fast": 30.0, "smart": 60.0}

_STRICT_UNSUPPORTED = {
    "default", "title", "format", "pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "minLength", "maxLength", "minItems", "maxItems",
}  # fmt: skip


_last_ok: dict[str, str | None] = {"provider": None}  # the provider that last answered, for /health


def active_provider(settings: Settings) -> str | None:
    """The provider that last answered a call in this process, else the first one configured."""
    return _last_ok["provider"] or settings.llm_provider


class LLMError(Exception):
    """The gateway could not produce a valid object. `code` is safe to show to a client."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ProviderUnavailable(Exception):
    """Rate limit, server error, timeout or connection failure: try the next provider."""


class Provider(Protocol):
    name: str

    def model_for(self, tier: Tier) -> str: ...

    def complete(self, *, model: str, system: str, user: str, schema: type[BaseModel], timeout: float) -> str:
        """Return the raw JSON text. Raise ProviderUnavailable for failures worth a fallback."""
        ...


# ---------------------------------------------------------------- schema helpers


def inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Replace every $ref with its definition and drop $defs (LLM schemas are small and acyclic)."""
    defs = schema.get("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                target = copy.deepcopy(defs[node["$ref"].rsplit("/", 1)[-1]])
                return walk({**target, **{k: v for k, v in node.items() if k != "$ref"}})
            return {k: walk(v) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


def to_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Rewrite a Pydantic JSON schema for strict structured output (Groq `json_schema`, strict: true):
    refs inlined, every property required, no extra properties, unsupported keywords removed."""

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            out = {}
            for key, value in node.items():
                if key in _STRICT_UNSUPPORTED:
                    continue
                # property names are data, not keywords: keep them even if they collide with one
                out[key] = {k: walk(v) for k, v in value.items()} if key == "properties" else walk(value)
            if out.get("type") == "object" or "properties" in out:
                out["required"] = list(out.get("properties", {}))
                out["additionalProperties"] = False
            return out
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(inline_refs(schema))


# ---------------------------------------------------------------- providers


class GeminiProvider:
    name = "gemini"

    def __init__(self, settings: Settings):
        from google import genai

        self._models = {"fast": settings.gemini_model_fast, "smart": settings.gemini_model_smart}
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def model_for(self, tier: Tier) -> str:
        return self._models[tier]

    def complete(self, *, model: str, system: str, user: str, schema: type[BaseModel], timeout: float) -> str:
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=inline_refs(schema.model_json_schema()),
            http_options=types.HttpOptions(timeout=int(timeout * 1000)),
        )
        try:
            response = self._client.models.generate_content(model=model, contents=user, config=config)
        except errors.APIError as exc:
            if exc.code == 429 or (exc.code or 0) >= 500:
                raise ProviderUnavailable(f"gemini HTTP {exc.code}") from exc
            raise LLMError("llm_request_rejected", f"Gemini rejected the request (HTTP {exc.code})") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"gemini {type(exc).__name__}") from exc
        return response.text or ""


class GroqProvider:
    name = "groq"

    def __init__(self, settings: Settings):
        import groq

        self._model = settings.groq_model
        self._client = groq.Groq(api_key=settings.groq_api_key, max_retries=0)

    def model_for(self, tier: Tier) -> str:
        return self._model

    def complete(self, *, model: str, system: str, user: str, schema: type[BaseModel], timeout: float) -> str:
        import groq

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "strict": True,
                "schema": to_strict_schema(schema.model_json_schema()),
            },
        }
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_format=response_format,
                timeout=timeout,
            )
        except (groq.RateLimitError, groq.InternalServerError, groq.APIConnectionError) as exc:
            # APITimeoutError is a subclass of APIConnectionError
            raise ProviderUnavailable(f"groq {type(exc).__name__}") from exc
        except groq.APIStatusError as exc:
            # 413: the request is over this plan's per-request token limit; another provider may take it
            if exc.status_code >= 500 or exc.status_code == 413:
                raise ProviderUnavailable(f"groq HTTP {exc.status_code}") from exc
            raise LLMError(
                "llm_request_rejected", f"Groq rejected the request (HTTP {exc.status_code})"
            ) from exc
        return response.choices[0].message.content or ""


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings):
        self._url = settings.ollama_url.rstrip("/")
        self._model = settings.ollama_model

    def model_for(self, tier: Tier) -> str:
        return self._model

    def complete(self, *, model: str, system: str, user: str, schema: type[BaseModel], timeout: float) -> str:
        payload = {
            "model": model,
            "stream": False,
            "format": inline_refs(schema.model_json_schema()),
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        try:
            # a local model on a laptop CPU is slow: give it more room than the hosted APIs
            response = httpx.post(f"{self._url}/api/chat", json=payload, timeout=timeout * 4)
            response.raise_for_status()
            return response.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ProviderUnavailable(f"ollama {type(exc).__name__}") from exc


def build_providers(settings: Settings) -> list[Provider]:
    """Configured providers in fallback order. Providers without a key are skipped."""
    providers: list[Provider] = []
    if settings.gemini_api_key:
        providers.append(GeminiProvider(settings))
    if settings.groq_api_key:
        providers.append(GroqProvider(settings))
    if settings.ollama_url:
        providers.append(OllamaProvider(settings))
    return providers


# ---------------------------------------------------------------- gateway


def cache_key(primary_model: str, schema: type[BaseModel], system: str, user: str) -> str:
    payload = json.dumps(
        [primary_model, schema.__name__, schema.model_json_schema(), system, user], sort_keys=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validation_feedback(exc: ValidationError) -> str:
    """Field paths and messages only; never the values the model produced."""
    lines = []
    for err in exc.errors(include_input=False, include_url=False)[:12]:
        where = ".".join(str(p) for p in err["loc"]) or "(root)"
        lines.append(f"- {where}: {err['msg']}")
    return "\n".join(lines)


def _ask(
    provider: Provider, model: str, schema: type[BaseModel], system: str, user: str, tier: Tier
) -> BaseModel:
    """One provider: call, validate, and retry once with the validation errors appended."""
    timeout = TIMEOUT_S[tier]
    raw = provider.complete(model=model, system=system, user=user, schema=schema, timeout=timeout)
    try:
        return schema.model_validate_json(raw)
    except ValidationError as first:
        logger.info(
            "llm provider=%s model=%s schema=%s outcome=invalid_retrying",
            provider.name,
            model,
            schema.__name__,
        )
        retry_user = (
            f"{user}\n\nYour previous reply did not match the required JSON schema:\n"
            f"{_validation_feedback(first)}\nReply again with corrected JSON only."
        )
    raw = provider.complete(model=model, system=system, user=retry_user, schema=schema, timeout=timeout)
    try:
        return schema.model_validate_json(raw)
    except ValidationError as second:
        raise LLMError(
            "llm_invalid_response", f"{provider.name} did not return a valid {schema.__name__}"
        ) from second


def generate_structured[T: BaseModel](
    schema: type[T],
    system: str,
    user: str,
    tier: Tier = "fast",
    *,
    db: Session,
    force_refresh: bool = False,
    providers: list[Provider] | None = None,
    settings: Settings | None = None,
) -> T:
    """Return a validated `schema` instance for the prompt. Raises LLMError if no provider can.

    `user` must already be PII-stripped (services.ingest.strip_pii).
    """
    settings = settings or get_settings()
    primary_model = settings.gemini_model_fast if tier == "fast" else settings.gemini_model_smart
    key = cache_key(primary_model, schema, system, user)

    if not force_refresh:
        cached = db.get(CacheEntry, key)
        if cached is not None:
            try:
                result = schema.model_validate(cached.value)
                logger.info("llm schema=%s tier=%s outcome=cache_hit", schema.__name__, tier)
                return result
            except ValidationError:
                pass  # schema changed since it was cached: fall through and regenerate

    providers = build_providers(settings) if providers is None else providers
    if not providers:
        raise LLMError(
            "llm_not_configured", "No LLM provider is configured (set GEMINI_API_KEY or GROQ_API_KEY)"
        )

    for provider in providers:
        model = provider.model_for(tier)
        started = time.perf_counter()
        try:
            result = _ask(provider, model, schema, system, user, tier)
        except ProviderUnavailable as exc:
            logger.warning(
                "llm provider=%s model=%s tier=%s schema=%s latency_ms=%d outcome=unavailable reason=%s",
                provider.name, model, tier, schema.__name__, (time.perf_counter() - started) * 1000, exc,
            )  # fmt: skip
            continue
        logger.info(
            "llm provider=%s model=%s tier=%s schema=%s latency_ms=%d outcome=ok",
            provider.name, model, tier, schema.__name__, (time.perf_counter() - started) * 1000,
        )  # fmt: skip
        _last_ok["provider"] = provider.name
        db.merge(CacheEntry(key=key, kind="llm", value=result.model_dump(mode="json")))
        db.commit()
        return result

    raise LLMError("llm_unavailable", "All LLM providers are rate-limited or unreachable right now")
