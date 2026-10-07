from fastapi import APIRouter, Depends

from app.db import models
from app.deps import get_current_profile
from app.routers import ERROR_RESPONSES
from app.schemas.api import Profile

router = APIRouter(tags=["profiles"], responses=ERROR_RESPONSES)


@router.get("/v1/me", operation_id="getMe", response_model=Profile)
def get_me(profile: models.Profile = Depends(get_current_profile)) -> models.Profile:
    return profile
