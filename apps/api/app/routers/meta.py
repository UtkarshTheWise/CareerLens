import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.catalogue import load_roles
from app.config import API_VERSION, Settings, get_settings
from app.deps import get_auth_subject, get_db
from app.errors import ApiError
from app.routers import ERROR_RESPONSES
from app.schemas.api import HealthResponse, Role
from app.services.llm import active_provider

logger = logging.getLogger("careerlens.health")

router = APIRouter(tags=["meta"], responses=ERROR_RESPONSES)


@router.get("/health", operation_id="getHealth", response_model=HealthResponse)
def get_health(settings: Settings = Depends(get_settings), db: Session = Depends(get_db)) -> HealthResponse:
    """Ok only if the database answers; the daily keep-alive ping therefore keeps Supabase awake too.
    `llm_provider` is the provider that last answered in this process (no LLM call is made here)."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("health check: database unreachable (%s)", type(exc).__name__)
        raise ApiError(503, "db_unavailable", "The database is not reachable right now") from exc
    return HealthResponse(status="ok", version=API_VERSION, llm_provider=active_provider(settings))


@router.get(
    "/v1/roles",
    operation_id="listRoles",
    response_model=list[Role],
    dependencies=[Depends(get_auth_subject)],
)
def list_roles() -> list[Role]:
    return list(load_roles())
