from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import models
from app.deps import get_analysis_for, get_db, get_profile_for, get_quiz_for
from app.routers import ERROR_RESPONSES
from app.routers.analyses import get_pipeline_deps
from app.schemas.api import (
    Error,
    Quiz,
    QuizAnswer,
    QuizAnswerFeedback,
    QuizCreate,
    QuizResult,
    QuizSummary,
)
from app.services import quiz_flow
from app.services.pipeline import PipelineDeps

router = APIRouter(tags=["quizzes"], responses=ERROR_RESPONSES)

Clock = Callable[[], datetime]


def get_clock() -> Clock:
    """The time source for quiz clocks. Tests override this dependency."""
    return lambda: datetime.now(UTC)


@router.post(
    "/v1/analyses/{analysis_id}/quizzes",
    operation_id="createQuiz",
    response_model=Quiz,
    status_code=201,
    responses={429: {"model": Error, "description": "Verify cooldown active or LLM quota exhausted"}},
)
def create_quiz(
    body: QuizCreate,
    analysis: models.Analysis = Depends(get_analysis_for),
    db: Session = Depends(get_db),
    deps: PipelineDeps = Depends(get_pipeline_deps),
    settings: Settings = Depends(get_settings),
    clock: Clock = Depends(get_clock),
) -> Quiz:
    now = clock()
    quiz = quiz_flow.start_quiz(db, analysis, body, deps, now, settings)
    return quiz_flow.created_view(quiz, now)


@router.get("/v1/quizzes/{quiz_id}", operation_id="getQuiz", response_model=Quiz)
def get_quiz(
    quiz: models.Quiz = Depends(get_quiz_for),
    db: Session = Depends(get_db),
    deps: PipelineDeps = Depends(get_pipeline_deps),
    settings: Settings = Depends(get_settings),
    clock: Clock = Depends(get_clock),
) -> Quiz:
    return quiz_flow.open_quiz(db, quiz, deps, clock(), settings)


@router.post(
    "/v1/quizzes/{quiz_id}/answers",
    operation_id="answerQuizQuestion",
    response_model=QuizAnswerFeedback,
    responses={
        409: {"model": Error, "description": "Question already answered, out of order, or quiz submitted"}
    },
)
def answer_quiz_question(
    body: QuizAnswer,
    quiz: models.Quiz = Depends(get_quiz_for),
    db: Session = Depends(get_db),
    deps: PipelineDeps = Depends(get_pipeline_deps),
    settings: Settings = Depends(get_settings),
    clock: Clock = Depends(get_clock),
) -> QuizAnswerFeedback:
    return quiz_flow.answer_question(db, quiz, body, deps, clock(), settings)


@router.post(
    "/v1/quizzes/{quiz_id}/submit",
    operation_id="submitQuiz",
    response_model=QuizResult,
    responses={409: {"model": Error, "description": "Already submitted"}},
)
def submit_quiz(
    quiz: models.Quiz = Depends(get_quiz_for),
    db: Session = Depends(get_db),
    deps: PipelineDeps = Depends(get_pipeline_deps),
    settings: Settings = Depends(get_settings),
    clock: Clock = Depends(get_clock),
) -> QuizResult:
    return quiz_flow.submit_or_fail(db, quiz, deps, clock(), settings)


@router.get(
    "/v1/quizzes/{quiz_id}/result",
    operation_id="getQuizResult",
    response_model=QuizResult,
    responses={409: {"model": Error, "description": "Quiz not submitted yet"}},
)
def get_quiz_result(
    quiz: models.Quiz = Depends(get_quiz_for),
    db: Session = Depends(get_db),
    deps: PipelineDeps = Depends(get_pipeline_deps),
    settings: Settings = Depends(get_settings),
    clock: Clock = Depends(get_clock),
) -> QuizResult:
    return quiz_flow.result_for(db, quiz, deps, clock(), settings)


@router.get("/v1/profiles/{profile_id}/quizzes", operation_id="listQuizzes", response_model=list[QuizSummary])
def list_quizzes(
    profile: models.Profile = Depends(get_profile_for),
    db: Session = Depends(get_db),
    deps: PipelineDeps = Depends(get_pipeline_deps),
    settings: Settings = Depends(get_settings),
    clock: Clock = Depends(get_clock),
) -> list[QuizSummary]:
    return quiz_flow.list_summaries(db, profile.id, deps, clock(), settings)
