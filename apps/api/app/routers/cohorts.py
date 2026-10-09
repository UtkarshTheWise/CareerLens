import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import catalogue
from app.db import models
from app.deps import get_db, require_staff
from app.errors import ApiError, not_found
from app.routers import ERROR_RESPONSES
from app.schemas.api import Band, Cohort, CohortInsights, CohortStudent, EvidenceLevel
from app.services import cohorts

# Cohort data is for placement staff only (docs/QUIZ.md rule 5): every route here needs `require_staff`.
router = APIRouter(tags=["cohorts"], responses=ERROR_RESPONSES, dependencies=[Depends(require_staff)])


def _cohort(db: Session, cohort_id: UUID) -> models.Cohort:
    cohort = db.get(models.Cohort, str(cohort_id))
    if cohort is None:
        raise not_found("Cohort")
    return cohort


def _role(role_id: str) -> str:
    if catalogue.get_role(role_id) is None:
        raise ApiError(422, "validation_error", f"Unknown role '{role_id}'", {"field": "role_id"})
    return role_id


MAX_SKILL_FILTERS = 10


def _student_query(
    at_risk_only: bool = False,
    skill: list[str] = Query(default=[]),
    skill_match: Literal["all", "any"] = "all",
    min_level: Literal["strong", "moderate", "weak", "unverified"] = "moderate",
    min_score: float | None = Query(default=None, ge=0, le=100),
    band: list[Band] = Query(default=[]),
    sort: Literal["score_asc", "score_desc", "coverage_desc", "name"] = "score_asc",
    limit: int | None = Query(default=None, ge=1, le=500),
) -> cohorts.StudentQuery:
    """Shared by the student list and the CSV export, so both return the same people."""
    if len(skill) > MAX_SKILL_FILTERS:
        raise ApiError(422, "validation_error", f"At most {MAX_SKILL_FILTERS} skills", {"field": "skill"})
    for skill_id in skill:
        if catalogue.get_skill(skill_id) is None:
            raise ApiError(422, "validation_error", f"Unknown skill '{skill_id}'", {"field": "skill"})
    return cohorts.StudentQuery(
        at_risk_only=at_risk_only,
        skills=tuple(skill),
        skill_match=skill_match,
        min_level=EvidenceLevel(min_level),
        min_score=min_score,
        bands=frozenset(band),
        sort=sort,
        limit=limit,
    )


@router.get("/v1/cohorts", operation_id="listCohorts", response_model=list[Cohort])
def list_cohorts(db: Session = Depends(get_db)) -> list[dict]:
    counts = dict(
        db.execute(
            select(models.Profile.cohort_id, func.count(models.Profile.id))
            .where(models.Profile.cohort_id.is_not(None))
            .group_by(models.Profile.cohort_id)
        ).all()
    )
    rows = db.scalars(select(models.Cohort).order_by(models.Cohort.name, models.Cohort.id))
    return [
        {
            "id": c.id,
            "name": c.name,
            "department": c.department,
            "year": c.year,
            "student_count": counts.get(c.id, 0),
        }
        for c in rows
    ]


@router.get(
    "/v1/cohorts/{cohort_id}/insights", operation_id="getCohortInsights", response_model=CohortInsights
)
def get_cohort_insights(cohort_id: UUID, role_id: str, db: Session = Depends(get_db)) -> CohortInsights:
    cohort = _cohort(db, cohort_id)
    rows, profiles = cohorts.load_rows(db, cohort.id, _role(role_id))
    return cohorts.aggregate(rows, profiles, cohort.id, role_id)


@router.get(
    "/v1/cohorts/{cohort_id}/students", operation_id="listCohortStudents", response_model=list[CohortStudent]
)
def list_cohort_students(
    cohort_id: UUID,
    role_id: str,
    query: cohorts.StudentQuery = Depends(_student_query),
    db: Session = Depends(get_db),
) -> list[CohortStudent]:
    cohort = _cohort(db, cohort_id)
    rows, _ = cohorts.load_rows(db, cohort.id, _role(role_id))
    return cohorts.students(rows, query)


@router.get(
    "/v1/cohorts/{cohort_id}/export",
    operation_id="exportCohort",
    response_class=Response,
    responses={200: {"description": "CSV file", "content": {"text/csv": {"schema": {"type": "string"}}}}},
)
def export_cohort(
    cohort_id: UUID,
    role_id: str,
    query: cohorts.StudentQuery = Depends(_student_query),
    db: Session = Depends(get_db),
) -> Response:
    cohort = _cohort(db, cohort_id)
    rows, _ = cohorts.load_rows(db, cohort.id, _role(role_id))
    body = cohorts.to_csv(cohorts.students(rows, query))
    stem = re.sub(r"[^A-Za-z0-9]+", "-", f"{cohort.name}-{role_id}").strip("-").lower()
    return Response(
        body, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{stem}.csv"'}
    )
