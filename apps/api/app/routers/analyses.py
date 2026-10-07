import copy

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import catalogue
from app.db import models
from app.deps import get_analysis_for, get_db, get_profile_for
from app.errors import ApiError, not_found
from app.routers import ERROR_RESPONSES
from app.schemas.api import (
    Analysis,
    AnalysisStart,
    AnalysisStatus,
    AnalysisSummary,
    Error,
    MilestoneUpdate,
    RoadmapMilestone,
    SimulationRequest,
    SimulationResult,
)
from app.services import scoring
from app.services.pipeline import PipelineDeps, run_analysis
from app.services.scoring_inputs import ScoringInputs, SimulationError

router = APIRouter(tags=["analyses"], responses=ERROR_RESPONSES)


def get_pipeline_deps() -> PipelineDeps:
    """The real LLM providers, GitHub client and page fetcher. Tests override this dependency."""
    return PipelineDeps()


@router.post(
    "/v1/profiles/{profile_id}/analyses",
    operation_id="startAnalysis",
    response_model=AnalysisStatus,
    status_code=202,
    responses={409: {"model": Error, "description": "Profile has no resume yet"}},
)
def start_analysis(
    body: AnalysisStart,
    background: BackgroundTasks,
    profile: models.Profile = Depends(get_profile_for),
    deps: PipelineDeps = Depends(get_pipeline_deps),
    db: Session = Depends(get_db),
) -> models.Analysis:
    if catalogue.get_role(body.role_id) is None:
        raise ApiError(422, "validation_error", f"Unknown role '{body.role_id}'", {"field": "role_id"})
    if not profile.has_resume:
        raise ApiError(409, "no_resume", "Upload a resume before starting an analysis")
    analysis = models.Analysis(profile_id=profile.id, role_id=body.role_id, status="queued", progress=0)
    db.add(analysis)
    db.commit()
    background.add_task(run_analysis, analysis.id, deps, body.force_refresh)
    return analysis


@router.get(
    "/v1/profiles/{profile_id}/analyses", operation_id="listAnalyses", response_model=list[AnalysisSummary]
)
def list_analyses(
    profile: models.Profile = Depends(get_profile_for), db: Session = Depends(get_db)
) -> list[models.Analysis]:
    stmt = (
        select(models.Analysis)
        .where(models.Analysis.profile_id == profile.id)
        .order_by(models.Analysis.created_at.desc(), models.Analysis.id)
    )
    return list(db.scalars(stmt))


@router.get("/v1/analyses/{analysis_id}", operation_id="getAnalysis", response_model=Analysis)
def get_analysis(analysis: models.Analysis = Depends(get_analysis_for)) -> models.Analysis:
    return analysis


def _ready(analysis: models.Analysis) -> None:
    if analysis.status != "done" or not analysis.report or not analysis.signals:
        raise ApiError(409, "analysis_not_ready", "This analysis hasn't finished yet")


@router.post(
    "/v1/analyses/{analysis_id}/simulate", operation_id="simulateAnalysis", response_model=SimulationResult
)
def simulate_analysis(
    body: SimulationRequest, analysis: models.Analysis = Depends(get_analysis_for)
) -> SimulationResult:
    """What-if on the stored scoring inputs: deterministic, no LLM and no GitHub call."""
    _ready(analysis)
    inputs = ScoringInputs.model_validate(analysis.signals)
    try:
        return scoring.simulate(inputs, body, analysis.role_id)
    except SimulationError as exc:
        raise ApiError(422, "validation_error", str(exc)) from exc


@router.patch(
    "/v1/analyses/{analysis_id}/roadmap/{milestone_id}",
    operation_id="updateMilestone",
    response_model=RoadmapMilestone,
)
def update_milestone(
    milestone_id: str,
    body: MilestoneUpdate,
    analysis: models.Analysis = Depends(get_analysis_for),
    db: Session = Depends(get_db),
) -> dict:
    """Tick a roadmap milestone. Does not change the score; a re-scan does."""
    _ready(analysis)
    report = copy.deepcopy(analysis.report)  # reassign below so SQLAlchemy sees the JSON change
    milestone = next((m for m in report["roadmap"] if m["id"] == milestone_id), None)
    if milestone is None:
        raise not_found("Milestone")
    milestone["done"] = body.done
    analysis.report = report
    db.commit()
    return milestone
