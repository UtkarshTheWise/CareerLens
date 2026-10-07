import logging
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import catalogue
from app.db import models
from app.deps import DEV_SUBJECT, get_auth_subject, get_current_profile, get_db, get_profile_for
from app.errors import ApiError
from app.routers import ERROR_RESPONSES
from app.schemas.api import Error, Profile, ProfileCreate, ProfileUpdate
from app.services.ingest import MAX_UPLOAD_BYTES, extract_text

logger = logging.getLogger("careerlens.profiles")

router = APIRouter(tags=["profiles"], responses=ERROR_RESPONSES)


def _check_references(db: Session, fields: dict) -> None:
    role_id, cohort_id = fields.get("target_role_id"), fields.get("cohort_id")
    if role_id is not None and catalogue.get_role(role_id) is None:
        raise ApiError(422, "validation_error", f"Unknown role '{role_id}'", {"field": "target_role_id"})
    if cohort_id is not None and db.get(models.Cohort, str(cohort_id)) is None:
        raise ApiError(422, "validation_error", "Unknown cohort", {"field": "cohort_id"})


def _to_columns(fields: dict) -> dict:
    if fields.get("cohort_id") is not None:
        fields["cohort_id"] = str(fields["cohort_id"])
    return fields


@router.get("/v1/me", operation_id="getMe", response_model=Profile)
def get_me(profile: models.Profile = Depends(get_current_profile)) -> models.Profile:
    return profile


@router.post("/v1/profiles", operation_id="createProfile", response_model=Profile, status_code=201)
def create_profile(
    body: ProfileCreate, subject: str = Depends(get_auth_subject), db: Session = Depends(get_db)
) -> models.Profile:
    fields = body.model_dump()
    _check_references(db, fields)
    profile = models.Profile(**_to_columns(fields))
    if subject != DEV_SUBJECT:
        taken = db.scalar(select(models.Profile.id).where(models.Profile.auth_subject == subject))
        if taken is not None:
            raise ApiError(409, "conflict", "This account already has a profile", {"profile_id": taken})
        profile.auth_subject = subject
    db.add(profile)
    db.commit()
    return profile


@router.get("/v1/profiles/{profile_id}", operation_id="getProfile", response_model=Profile)
def get_profile(profile: models.Profile = Depends(get_profile_for)) -> models.Profile:
    return profile


@router.patch("/v1/profiles/{profile_id}", operation_id="updateProfile", response_model=Profile)
def update_profile(
    body: ProfileUpdate, profile: models.Profile = Depends(get_profile_for), db: Session = Depends(get_db)
) -> models.Profile:
    fields = body.model_dump(exclude_unset=True)
    if fields.get("name") is None and "name" in fields:
        raise ApiError(422, "validation_error", "Name cannot be empty", {"field": "name"})
    if "portfolio_urls" in fields and fields["portfolio_urls"] is None:
        fields["portfolio_urls"] = []
    _check_references(db, fields)
    for key, value in _to_columns(fields).items():
        setattr(profile, key, value)
    db.commit()
    return profile


@router.delete("/v1/profiles/{profile_id}", operation_id="deleteProfile", status_code=204)
def delete_profile(
    profile: models.Profile = Depends(get_profile_for), db: Session = Depends(get_db)
) -> Response:
    """Removes the profile with its documents, analyses and applications ("delete my data")."""
    db.delete(profile)
    db.commit()
    return Response(status_code=204)


@router.post(
    "/v1/profiles/{profile_id}/documents",
    operation_id="uploadDocument",
    response_model=Profile,
    responses={413: {"model": Error, "description": "File too large"}},
)
def upload_document(
    kind: Literal["resume", "linkedin"] = Form(...),
    file: UploadFile = File(...),
    profile: models.Profile = Depends(get_profile_for),
    db: Session = Depends(get_db),
) -> models.Profile:
    data = file.file.read(MAX_UPLOAD_BYTES + 1)  # one byte past the limit is enough to reject
    extracted = extract_text(file.filename, data)
    for old in [d for d in profile.documents if d.kind == kind]:
        profile.documents.remove(old)  # a new upload replaces the previous one of the same kind
    profile.documents.append(
        models.Document(
            kind=kind, filename=file.filename, text=extracted.text, page_count=extracted.page_count
        )
    )
    db.commit()
    logger.info("Stored %s document for profile %s (%d bytes)", kind, profile.id, len(data))
    return profile
