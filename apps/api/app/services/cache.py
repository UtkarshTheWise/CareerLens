"""Cache of external calls in the `cache` table, with an optional expiry (GitHub: 24 h)."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import CacheEntry


def cache_get(db: Session, key: str) -> Any | None:
    """The cached value, or None if missing or expired. Expired rows are left for the next write."""
    entry = db.get(CacheEntry, key)
    if entry is None:
        return None
    if entry.expires_at is not None and entry.expires_at <= datetime.now(UTC):
        return None
    return entry.value


def cache_set(db: Session, key: str, kind: str, value: Any, ttl: timedelta | None = None) -> None:
    expires_at = datetime.now(UTC) + ttl if ttl is not None else None
    db.merge(CacheEntry(key=key, kind=kind, value=value, expires_at=expires_at))
    db.commit()
