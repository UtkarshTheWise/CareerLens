"""Loaders for the curated catalogues in data/. B2 adds skills and resources here."""

from functools import lru_cache
from pathlib import Path

import yaml

from app.config import DATA_DIR
from app.schemas.api import Role


@lru_cache
def load_roles(path: Path | None = None) -> tuple[Role, ...]:
    raw = yaml.safe_load((path or DATA_DIR / "roles.yaml").read_text(encoding="utf-8"))
    return tuple(Role.model_validate(r) for r in raw["roles"])


def get_role(role_id: str) -> Role | None:
    return next((r for r in load_roles() if r.id == role_id), None)
