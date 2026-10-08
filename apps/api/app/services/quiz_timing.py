"""Server-side clocks for verify quizzes (docs/QUIZ.md section 4). Pure over the rows and a `now`.

A question's clock starts when it is first served (`getQuiz`), never when the quiz is created. An answer
more than 10 s after the limit scores 0. A question left unanswered past limit + grace is recorded as
timed out the next time anything touches the quiz. A quiz is auto-submitted once the whole time budget
has passed. A verify quiz whose first question was never served is closed after 30 minutes as
*abandoned*: it has no effect on evidence, so not starting never costs a student anything.
"""

from datetime import datetime, timedelta

from app.db import models

GRACE_S = 10
TOTAL_SLACK_S = 60  # on top of the sum of limits and per-question grace, for network gaps between questions
ABANDON_AFTER = timedelta(minutes=30)


def current_question(quiz: models.Quiz) -> models.QuizQuestion | None:
    """The first question without an answer, in order."""
    return next((q for q in quiz.questions if q.answer is None), None)


def is_overdue(question: models.QuizQuestion, now: datetime) -> bool:
    """Served, unanswered and past its limit plus grace."""
    if question.time_limit_s is None or question.served_at is None or question.answer is not None:
        return False
    return now > question.served_at + timedelta(seconds=question.time_limit_s + GRACE_S)


def first_served_at(quiz: models.Quiz) -> datetime | None:
    served = [q.served_at for q in quiz.questions if q.served_at is not None]
    return min(served) if served else None


def total_deadline(quiz: models.Quiz) -> datetime | None:
    """When the whole verify quiz ends by itself; None until the first question is served."""
    start = first_served_at(quiz)
    if start is None:
        return None
    seconds = sum((q.time_limit_s or 0) + GRACE_S for q in quiz.questions) + TOTAL_SLACK_S
    return start + timedelta(seconds=seconds)


def is_abandoned(quiz: models.Quiz, now: datetime) -> bool:
    return first_served_at(quiz) is None and now >= quiz.created_at + ABANDON_AFTER


def timed_out_answer(question: models.QuizQuestion, now: datetime) -> models.QuizAnswer:
    """The record for a question whose time ran out with no answer."""
    spent = int((question.time_limit_s or 0) * 1000)
    return models.QuizAnswer(
        question_id=question.id, timed_out=True, time_taken_ms=spent, focus_lost_count=0, answered_at=now
    )


def time_remaining_s(question: models.QuizQuestion, now: datetime) -> int | None:
    if question.time_limit_s is None or question.served_at is None or question.answer is not None:
        return None
    left = question.time_limit_s - (now - question.served_at).total_seconds()
    return max(0, int(left))
