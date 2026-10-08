"""The life of a quiz: start, open, answer, submit, result (docs/QUIZ.md sections 1, 3 and 4).

Everything takes `now` so tests control the clock. `settle` is run first by every request that touches a
verify quiz: it records overdue questions as timed out, closes a never-started quiz as abandoned and
auto-submits a quiz whose whole time budget has passed. Answer keys only leave through `quiz_views`.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import models
from app.errors import ApiError, not_found
from app.schemas.api import (
    Quiz,
    QuizAnswer,
    QuizAnswerFeedback,
    QuizCreate,
    QuizResult,
    QuizSummary,
    ReviewTopic,
    SourceRef,
)
from app.services import quiz as quiz_service
from app.services.llm import LLMError
from app.services.pipeline import PipelineDeps
from app.services.quiz_effects import apply_verify_result
from app.services.quiz_grading import (
    grade_mcq,
    grade_short_answers,
    grade_without_answer,
    has_answer,
    quiz_score,
    understanding_for,
)
from app.services.quiz_timing import (
    current_question,
    is_abandoned,
    is_overdue,
    timed_out_answer,
    total_deadline,
)
from app.services.quiz_views import CATEGORY_TOPIC, feedback_out, quiz_out, summary_out, topic_text

logger = logging.getLogger("careerlens.quiz")

STRONG_Q = 0.7  # a question at or above this is a strength; below it is a review topic
MAX_STRENGTHS = 5
MAX_REVIEW_TOPICS = 6


def iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def retake_at(quiz: models.Quiz, settings: Settings) -> datetime | None:
    if quiz.mode != "verify":
        return None
    return quiz.created_at + timedelta(minutes=settings.quiz_cooldown_minutes)


# ---------------------------------------------------------------- settling a verify quiz


def _close_abandoned(db: Session, quiz: models.Quiz, now: datetime, settings: Settings) -> None:
    """Never started: closed with no score and no effect on evidence."""
    quiz.status, quiz.abandoned, quiz.auto_submitted = "submitted", True, True
    quiz.submitted_at, quiz.score, quiz.understanding = now, None, None
    result = QuizResult(
        quiz_id=quiz.id, mode=quiz.mode, score=0, understanding=None, per_question=[], strengths=[],
        review_topics=[], retake_available_at=retake_at(quiz, settings),
    )  # fmt: skip
    quiz.result = result.model_dump(mode="json")
    db.commit()


def settle(
    db: Session,
    quiz: models.Quiz,
    deps: PipelineDeps,
    now: datetime,
    settings: Settings,
    *,
    record_timeouts: bool = True,
) -> None:
    if quiz.mode != "verify" or quiz.status != "in_progress":
        return
    if is_abandoned(quiz, now):
        _close_abandoned(db, quiz, now, settings)
        return
    if record_timeouts:
        changed = False
        for question in quiz.questions:
            if question.answer is None and is_overdue(question, now):
                question.answer = timed_out_answer(question, now)
                changed = True
        if changed:
            db.commit()
    deadline = total_deadline(quiz)
    if deadline is not None and now > deadline:
        if not any(has_answer(q.answer) for q in quiz.questions):
            # Opened but never answered: the same as not starting. Walking away never lowers a score.
            _close_abandoned(db, quiz, now, settings)
            return
        try:
            submit_quiz(db, quiz, deps, now, settings, auto=True)
        except (LLMError, ApiError) as exc:
            db.rollback()  # grading failed: answers stay recorded, the next request tries again
            logger.warning("auto-submit of quiz %s postponed: %s", quiz.id, getattr(exc, "code", "error"))


# ---------------------------------------------------------------- start and open


def start_quiz(
    db: Session,
    analysis: models.Analysis,
    body: QuizCreate,
    deps: PipelineDeps,
    now: datetime,
    settings: Settings,
) -> models.Quiz:
    if body.mode.value == "verify":
        quiz_service.find_project(analysis, body.project_id)  # 404 / 409 before any cooldown talk
        prior = list(
            db.scalars(
                select(models.Quiz)
                .where(
                    models.Quiz.profile_id == analysis.profile_id,
                    models.Quiz.project_id == body.project_id,
                    models.Quiz.mode == "verify",
                )
                .order_by(models.Quiz.created_at.desc(), models.Quiz.id)
            )
        )
        for quiz in prior:
            settle(db, quiz, deps, now, settings)
        open_quiz_ = next((q for q in prior if q.status == "in_progress"), None)
        if open_quiz_ is not None:
            raise ApiError(
                409, "quiz_in_progress", "You already have a verify check open for this project.",
                {"quiz_id": open_quiz_.id},
            )  # fmt: skip
        if prior and settings.quiz_cooldown_minutes > 0:
            available = retake_at(prior[0], settings)
            if now < available:
                raise ApiError(
                    429, "quiz_cooldown", "You can retake the verify check a little later.",
                    {"retake_available_at": iso(available)},
                )  # fmt: skip
    return quiz_service.create_quiz(db, analysis, body, deps, now=now)


def created_view(quiz: models.Quiz, now: datetime) -> Quiz:
    """The response of createQuiz: a verify quiz shows no questions until the student starts it."""
    return quiz_out(quiz, now, started=quiz.mode == "practice")


def open_quiz(db: Session, quiz: models.Quiz, deps: PipelineDeps, now: datetime, settings: Settings) -> Quiz:
    """getQuiz. In verify mode this serves the current question and starts its clock."""
    settle(db, quiz, deps, now, settings)
    if quiz.mode == "verify" and quiz.status == "in_progress":
        current = current_question(quiz)
        if current is not None and current.served_at is None:
            current.served_at = now
            db.commit()
    return quiz_out(quiz, now, started=True)


# ---------------------------------------------------------------- answering


def _find_question(quiz: models.Quiz, question_id: str) -> models.QuizQuestion:
    question = next((q for q in quiz.questions if q.id == question_id), None)
    if question is None:
        raise not_found("Question")
    return question


def answer_question(
    db: Session,
    quiz: models.Quiz,
    body: QuizAnswer,
    deps: PipelineDeps,
    now: datetime,
    settings: Settings,
) -> QuizAnswerFeedback:
    settle(db, quiz, deps, now, settings, record_timeouts=False)  # a late answer is recorded below, as late
    if quiz.status == "submitted":
        raise ApiError(409, "quiz_submitted", "This quiz has already been submitted.")
    question = _find_question(quiz, body.question_id)
    if question.answer is not None:
        raise ApiError(409, "already_answered", "This question has already been answered.")
    verify = quiz.mode == "verify"
    if verify:
        current = current_question(quiz)
        if current is None or current.id != question.id:
            raise ApiError(409, "out_of_order", "Answer the questions in order, one at a time.")
        if question.served_at is None:
            question.served_at = now
    if question.type == "mcq":
        if body.choice_id is not None and body.choice_id not in {o["id"] for o in question.options}:
            raise ApiError(
                422, "validation_error", "Unknown choice for this question", {"field": "choice_id"}
            )
    late = verify and is_overdue(question, now)
    answer = models.QuizAnswer(
        question_id=question.id,
        choice_id=body.choice_id if question.type == "mcq" else None,
        text=(body.text or "").strip() or None if question.type == "short_answer" else None,
        time_taken_ms=max(0, body.time_taken_ms),
        focus_lost_count=max(0, body.focus_lost_count),
        timed_out=late,
        answered_at=now,
    )
    if verify:  # graded at submit; nothing but "recorded" goes back
        question.answer = answer
        db.commit()
        return feedback_out(question, reveal=False)
    # Practice: grade first, attach the answer to the session afterwards. The grading call commits when it
    # succeeds; an answer attached earlier would be saved ungraded if the grader then failed, and a resend
    # would be refused as "already answered".
    try:
        if question.type == "mcq":
            grade_mcq(question, answer)
        elif has_answer(answer):
            grade_short_answers(db, [(question, answer)], tier="fast", providers=deps.providers)
        else:
            grade_without_answer(question, answer)
    except LLMError as exc:
        db.rollback()
        if exc.code == "llm_key_rejected":
            raise ApiError(400, "invalid_llm_key", exc.message) from exc
        raise ApiError(
            503,
            "llm_unavailable",
            "The grader is busy right now. Your answer wasn't lost: try sending it again.",
        ) from exc
    question.answer = answer
    db.commit()
    return feedback_out(question, reveal=True)


# ---------------------------------------------------------------- submitting and the result


def build_result(quiz: models.Quiz, settings: Settings) -> QuizResult:
    strengths: list[str] = []
    weak: list[tuple[float, models.QuizQuestion]] = []
    for question in quiz.questions:
        score = question.answer.score if question.answer and question.answer.score is not None else 0.0
        if score >= STRONG_Q:
            where = f" in {question.source_ref['path']}" if question.source_ref else ""
            text = f"Good grasp of {CATEGORY_TOPIC.get(question.category, question.category)}{where}"
            if text not in strengths:
                strengths.append(text)
        else:
            weak.append((score, question))
    weak.sort(key=lambda pair: (pair[0], pair[1].order))
    topics = [
        ReviewTopic(topic=topic_text(q), source_ref=SourceRef(**q.source_ref) if q.source_ref else None)
        for _, q in weak[:MAX_REVIEW_TOPICS]
    ]
    verify = quiz.mode == "verify"
    return QuizResult(
        quiz_id=quiz.id,
        mode=quiz.mode,
        score=quiz.score or 0.0,
        understanding=quiz.understanding,
        per_question=[feedback_out(q, reveal=True) for q in quiz.questions],
        strengths=strengths[:MAX_STRENGTHS],
        review_topics=topics,
        focus_lost_total=sum((q.answer.focus_lost_count or 0) for q in quiz.questions if q.answer)
        if verify
        else None,
        retake_available_at=retake_at(quiz, settings),
    )


def submit_quiz(
    db: Session,
    quiz: models.Quiz,
    deps: PipelineDeps,
    now: datetime,
    settings: Settings,
    *,
    auto: bool = False,
) -> QuizResult:
    """Grade what is left and close the quiz. Raises LLMError if the grader can't answer; nothing is
    committed then, so every recorded answer survives and the student can submit again."""
    if quiz.status == "submitted":
        raise ApiError(409, "already_submitted", "This quiz has already been submitted.")
    verify = quiz.mode == "verify"
    pending = []
    for question in quiz.questions:
        if question.answer is None:
            question.answer = models.QuizAnswer(
                question_id=question.id,
                answered_at=now,
                time_taken_ms=0,
                focus_lost_count=0,
                timed_out=verify and is_overdue(question, now),
            )
        answer = question.answer
        if answer.score is not None:
            continue  # a practice answer, graded when it was sent
        if question.type == "mcq":
            grade_mcq(question, answer)
        elif has_answer(answer):
            pending.append((question, answer))
        else:
            grade_without_answer(question, answer)
    grade_short_answers(db, pending, tier="smart" if verify else "fast", providers=deps.providers)

    quiz.score = quiz_score([(q.type, q.answer.score or 0.0) for q in quiz.questions])
    quiz.understanding = understanding_for(quiz.score).value if verify else None
    quiz.status, quiz.submitted_at, quiz.auto_submitted = "submitted", now, auto
    effects = apply_verify_result(db, quiz, deps) if verify else None  # practice never changes evidence
    result = build_result(quiz, settings)
    if effects is not None:
        result = result.model_copy(update={"score_update": effects[0], "flag": effects[1]})
    quiz.result = result.model_dump(mode="json")
    db.commit()
    return result


def submit_or_fail(
    db: Session, quiz: models.Quiz, deps: PipelineDeps, now: datetime, settings: Settings
) -> QuizResult:
    """submitQuiz: settle first, then grade; a grader outage is a retryable 503."""
    settle(db, quiz, deps, now, settings)
    try:
        return submit_quiz(db, quiz, deps, now, settings)
    except LLMError as exc:
        db.rollback()
        if exc.code == "llm_key_rejected":
            raise ApiError(400, "invalid_llm_key", exc.message) from exc
        raise ApiError(
            503,
            "llm_unavailable",
            "The grader is busy right now. Your answers are saved: try submitting again.",
        ) from exc


def result_for(
    db: Session, quiz: models.Quiz, deps: PipelineDeps, now: datetime, settings: Settings
) -> QuizResult:
    settle(db, quiz, deps, now, settings)
    if quiz.status != "submitted" or quiz.result is None:
        raise ApiError(409, "not_submitted", "This quiz hasn't been submitted yet.")
    return QuizResult.model_validate(quiz.result)


def list_summaries(
    db: Session, profile_id: str, deps: PipelineDeps, now: datetime, settings: Settings
) -> list[QuizSummary]:
    quizzes = list(
        db.scalars(
            select(models.Quiz)
            .where(models.Quiz.profile_id == profile_id)
            .order_by(models.Quiz.created_at.desc(), models.Quiz.id)
        )
    )
    for quiz in quizzes:
        settle(db, quiz, deps, now, settings)
    return [summary_out(q) for q in quizzes]
