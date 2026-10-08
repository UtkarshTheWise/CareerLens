"""Bring your own key: a student's own Gemini or Groq key, used for their requests only.

The web app sends `X-LLM-Provider` and `X-LLM-Key` on the operations that call a model. The key is held
in memory for the request (an analysis keeps it for its background job), is never stored, cached or
logged, and when it is present the shared keys are never used as a fallback. These two headers are not
part of contracts/openapi.yaml; they are optional and every other client ignores them.
"""

import re

from fastapi import Header, Request

from app.config import Settings, get_settings
from app.errors import ApiError
from app.services.llm import GeminiProvider, GroqProvider, Provider

PROVIDER_HEADER = "X-LLM-Provider"
KEY_HEADER = "X-LLM-Key"
_KEY = re.compile(r"[\x21-\x7e]{20,200}")  # printable ASCII, no whitespace


def build_user_provider(name: str, key: str, settings: Settings) -> Provider:
    """Tests replace this: it is the only place a real client is made from a student's key."""
    own = settings.model_copy(update={"gemini_api_key": key, "groq_api_key": key})
    provider = GeminiProvider(own) if name == "gemini" else GroqProvider(own)
    provider.user_key = True
    return provider


def user_providers(provider: str | None, key: str | None, settings: Settings) -> list[Provider] | None:
    """None when the student sent no key; otherwise exactly one provider built from it."""
    provider, key = (provider or "").strip().lower(), (key or "").strip()
    if not provider and not key:
        return None
    if provider not in ("gemini", "groq"):
        raise ApiError(422, "invalid_llm_key", "Choose Gemini or Groq for your own key.")
    if not _KEY.fullmatch(key):
        raise ApiError(422, "invalid_llm_key", "That does not look like an API key. Paste it again.")
    return [build_user_provider(provider, key, settings)]


def has_user_key(request: Request) -> bool:
    return bool(request.headers.get(KEY_HEADER, "").strip())


def get_user_providers(
    x_llm_provider: str | None = Header(default=None, alias=PROVIDER_HEADER, include_in_schema=False),
    x_llm_key: str | None = Header(default=None, alias=KEY_HEADER, include_in_schema=False),
) -> list[Provider] | None:
    return user_providers(x_llm_provider, x_llm_key, get_settings())
