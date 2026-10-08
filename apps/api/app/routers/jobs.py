from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.deps import get_auth_subject, get_db, load_profile
from app.errors import ApiError
from app.rate_limit import limited
from app.routers import ERROR_RESPONSES
from app.schemas.api import Error, JobMatch, JobMatchRequest
from app.services import matching
from app.services.llm import Provider
from app.services.scoring_inputs import ScoringInputs

router = APIRouter(tags=["jobs"], responses=ERROR_RESPONSES)


def get_llm_providers() -> list[Provider] | None:
    """None means the configured LLM providers. Tests override this dependency."""
    return None


@router.post(
    "/v1/jobs/match",
    operation_id="matchJob",
    dependencies=[Depends(limited("match", "rate_limit_match_per_hour"))],
    response_model=JobMatch,
    responses={409: {"model": Error, "description": "Profile has no completed analysis"}},
)
def match_job(
    body: JobMatchRequest,
    subject: str = Depends(get_auth_subject),
    db: Session = Depends(get_db),
    providers: list[Provider] | None = Depends(get_llm_providers),
) -> JobMatch:
    """Match a job posting against the profile's latest finished analysis (no GitHub call)."""
    profile = load_profile(db, subject, body.profile_id)
    analysis = db.scalar(
        select(models.Analysis)
        .where(
            models.Analysis.profile_id == profile.id,
            models.Analysis.status == "done",
            models.Analysis.signals.is_not(None),
        )
        .order_by(models.Analysis.created_at.desc(), models.Analysis.id)
        .limit(1)
    )
    if analysis is None:
        raise ApiError(409, "no_analysis", "Run an analysis before matching jobs")
    posting, notes = matching.normalize_posting(body.posting, db, providers=providers)
    return matching.match(ScoringInputs.model_validate(analysis.signals), posting, notes)
