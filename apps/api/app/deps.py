from collections.abc import Iterator
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import models
from app.db.base import SessionLocal
from app.errors import ApiError, not_found

DEV_SUBJECT = "dev"


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _bearer_token(request: Request) -> str | None:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    return token.strip() or None if scheme.lower() == "bearer" else None


def get_auth_subject(request: Request, settings: Settings = Depends(get_settings)) -> str:
    """Who is calling. DEV_AUTH=1 accepts any request as the demo user."""
    if settings.dev_auth:
        return DEV_SUBJECT
    if _bearer_token(request) is None:
        raise ApiError(401, "unauthorized", "Missing bearer token")
    # TODO(progress): verify the Supabase JWT with SUPABASE_JWT_SECRET and return its `sub` (B8).
    raise ApiError(401, "unauthorized", "Token verification is not available yet; run with DEV_AUTH=1")


def demo_profile(db: Session) -> models.Profile:
    """The synthetic profile behind DEV_AUTH. Created on first use."""
    profile = db.scalar(select(models.Profile).where(models.Profile.auth_subject == DEV_SUBJECT))
    if profile is None:
        profile = models.Profile(
            auth_subject=DEV_SUBJECT,
            name="Demo Student",
            target_role_id="sde-backend",
            department="CSE",
            portfolio_urls=[],
        )
        db.add(profile)
        db.commit()
    return profile


def get_current_profile(
    subject: str = Depends(get_auth_subject), db: Session = Depends(get_db)
) -> models.Profile:
    if subject == DEV_SUBJECT:
        return demo_profile(db)
    profile = db.scalar(select(models.Profile).where(models.Profile.auth_subject == subject))
    if profile is None:
        raise ApiError(404, "not_found", "No profile for this user yet")
    return profile


def load_profile(db: Session, subject: str, profile_id: UUID | str) -> models.Profile:
    """The profile with this id, if the caller may see it. DEV_AUTH sees every profile."""
    profile = db.get(models.Profile, str(profile_id))
    if profile is None or (subject != DEV_SUBJECT and profile.auth_subject != subject):
        raise not_found("Profile")
    return profile


def get_profile_for(
    profile_id: UUID, subject: str = Depends(get_auth_subject), db: Session = Depends(get_db)
) -> models.Profile:
    """The profile in the path, if the caller may see it."""
    return load_profile(db, subject, profile_id)


def get_application_for(
    application_id: UUID, subject: str = Depends(get_auth_subject), db: Session = Depends(get_db)
) -> models.Application:
    """The application in the path, if the caller owns its profile."""
    application = db.get(models.Application, str(application_id))
    if application is None or (subject != DEV_SUBJECT and application.profile.auth_subject != subject):
        raise not_found("Application")
    return application


def get_analysis_for(
    analysis_id: UUID, subject: str = Depends(get_auth_subject), db: Session = Depends(get_db)
) -> models.Analysis:
    """The analysis in the path, if the caller owns its profile."""
    analysis = db.get(models.Analysis, str(analysis_id))
    if analysis is None or (subject != DEV_SUBJECT and analysis.profile.auth_subject != subject):
        raise not_found("Analysis")
    return analysis


def get_quiz_for(
    quiz_id: UUID, subject: str = Depends(get_auth_subject), db: Session = Depends(get_db)
) -> models.Quiz:
    """The quiz in the path, if the caller owns its profile."""
    quiz = db.get(models.Quiz, str(quiz_id))
    if quiz is None or (subject != DEV_SUBJECT and quiz.profile.auth_subject != subject):
        raise not_found("Quiz")
    return quiz
