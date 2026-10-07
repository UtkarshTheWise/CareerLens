from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.deps import get_application_for, get_auth_subject, get_db, load_profile
from app.routers import ERROR_RESPONSES
from app.schemas.api import Application, ApplicationCreate, ApplicationUpdate

router = APIRouter(tags=["applications"], responses=ERROR_RESPONSES)


@router.get("/v1/applications", operation_id="listApplications", response_model=list[Application])
def list_applications(
    profile_id: UUID, subject: str = Depends(get_auth_subject), db: Session = Depends(get_db)
) -> list[models.Application]:
    profile = load_profile(db, subject, profile_id)
    stmt = (
        select(models.Application)
        .where(models.Application.profile_id == profile.id)
        .order_by(models.Application.created_at.desc(), models.Application.id)
    )
    return list(db.scalars(stmt))


@router.post(
    "/v1/applications", operation_id="createApplication", response_model=Application, status_code=201
)
def create_application(
    body: ApplicationCreate, subject: str = Depends(get_auth_subject), db: Session = Depends(get_db)
) -> models.Application:
    profile = load_profile(db, subject, body.profile_id)
    fields = body.model_dump(exclude={"profile_id", "status", "deadline"})
    application = models.Application(
        profile_id=profile.id,
        status=body.status.value if body.status else "saved",
        deadline=body.deadline.isoformat() if body.deadline else None,
        **fields,
    )
    if application.status == "applied":
        application.applied_at = datetime.now(UTC)
    db.add(application)
    db.commit()
    return application


@router.patch(
    "/v1/applications/{application_id}", operation_id="updateApplication", response_model=Application
)
def update_application(
    body: ApplicationUpdate,
    application: models.Application = Depends(get_application_for),
    db: Session = Depends(get_db),
) -> models.Application:
    changes = body.model_dump(exclude_unset=True)
    if "status" in changes:
        if changes["status"] is None:
            changes.pop("status")  # status can't be cleared
        else:
            changes["status"] = changes["status"].value
            # Moving to "applied" stamps the time unless the caller gave one.
            if changes["status"] == "applied" and application.applied_at is None:
                changes.setdefault("applied_at", datetime.now(UTC))
    if "deadline" in changes:
        changes["deadline"] = changes["deadline"].isoformat() if changes["deadline"] else None
    for name, value in changes.items():
        setattr(application, name, value)
    db.commit()
    return application


@router.delete("/v1/applications/{application_id}", operation_id="deleteApplication", status_code=204)
def delete_application(
    application: models.Application = Depends(get_application_for), db: Session = Depends(get_db)
) -> Response:
    db.delete(application)
    db.commit()
    return Response(status_code=204)
