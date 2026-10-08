"""Supabase access-token verification.

A token is accepted only if its signature checks out against a key we hold, it has not expired, it was
issued for the `authenticated` audience (and, when SUPABASE_URL is set, by that project), and it names a
subject. The algorithm is never taken on trust from the token: HS256 is checked against SUPABASE_JWT_SECRET,
ES256/RS256 against the project's published signing keys (JWKS), and anything else, including `none`, is
refused. Every failure is the same generic 401, so a caller learns nothing about why.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient

from app.config import Settings
from app.errors import ApiError

logger = logging.getLogger("careerlens.auth")

AUDIENCE = "authenticated"
JWKS_TIMEOUT_S = 5.0
JWKS_LIFESPAN_S = 3600
ASYMMETRIC = ("ES256", "RS256")


@dataclass(frozen=True)
class Claims:
    sub: str
    email: str | None = None
    app_role: str | None = None  # Supabase `app_metadata.role`: set by an admin, never by the user


def _unauthorized() -> ApiError:
    return ApiError(401, "unauthorized", "Invalid or expired sign-in. Please sign in again.")


def issuer_for(settings: Settings) -> str | None:
    return f"{settings.supabase_url.rstrip('/')}/auth/v1" if settings.supabase_url else None


@lru_cache
def jwks_client_for(supabase_url: str) -> PyJWKClient:
    """The project's signing keys, cached for an hour. Tests replace this function."""
    uri = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(uri, cache_keys=True, lifespan=JWKS_LIFESPAN_S, timeout=JWKS_TIMEOUT_S)


def _key_for(token: str, algorithm: str, settings: Settings) -> Any:
    if algorithm == "HS256":
        if not settings.supabase_jwt_secret:
            raise _unauthorized()
        return settings.supabase_jwt_secret
    if algorithm in ASYMMETRIC and settings.supabase_url:
        return jwks_client_for(settings.supabase_url).get_signing_key_from_jwt(token).key
    raise _unauthorized()


def verify_token(token: str, settings: Settings) -> Claims:
    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
        payload = jwt.decode(
            token,
            _key_for(token, str(algorithm), settings),
            algorithms=[algorithm],
            audience=AUDIENCE,
            issuer=issuer_for(settings),
            options={"require": ["exp", "sub"]},
        )
    except ApiError:
        raise
    except jwt.PyJWTError as exc:
        logger.info("token rejected: %s", type(exc).__name__)  # the class only: never the token
        raise _unauthorized() from exc
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise _unauthorized()
    app_metadata = payload.get("app_metadata")
    role = app_metadata.get("role") if isinstance(app_metadata, dict) else None
    email = payload.get("email")
    return Claims(
        sub=sub,
        email=email if isinstance(email, str) else None,
        app_role=role if isinstance(role, str) else None,
    )
