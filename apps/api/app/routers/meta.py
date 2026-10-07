from fastapi import APIRouter, Depends

from app.catalogue import load_roles
from app.config import API_VERSION, Settings, get_settings
from app.deps import get_auth_subject
from app.routers import ERROR_RESPONSES
from app.schemas.api import HealthResponse, Role

router = APIRouter(tags=["meta"], responses=ERROR_RESPONSES)


@router.get("/health", operation_id="getHealth", response_model=HealthResponse)
def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", version=API_VERSION, llm_provider=settings.llm_provider)


@router.get(
    "/v1/roles",
    operation_id="listRoles",
    response_model=list[Role],
    dependencies=[Depends(get_auth_subject)],
)
def list_roles() -> list[Role]:
    return list(load_roles())
