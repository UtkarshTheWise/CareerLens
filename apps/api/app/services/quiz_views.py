"""Quiz rows -> contract models. The only place answer keys are turned into response fields.

`question_out` and `quiz_out` never read a key column. `feedback_out(reveal=False)` returns only what the
student already knows (their own answer). Keys appear through `feedback_out(reveal=True)`, which callers use
for a graded practice answer and for a submitted quiz.
"""

from datetime import datetime

from app.db import models
from app.schemas.api import (
    CodeSnippet,
    KeyPointResult,
    Quiz,
    QuizAnswerFeedback,
    QuizOption,
    QuizQuestion,
    QuizSummary,
    SourceRef,
)
from app.services.quiz_timing import current_question, time_remaining_s

CATEGORY_TOPIC = {
    "code_reading": "how the code behaves",
    "architecture": "the flow through the project",
    "design_decision": "a design decision",
    "debugging": "a failure case",
    "extension": "how to extend it",
    "claim_check": "where a technology is used",
    "process": "your process",
    "outcome": "the outcome",
    "critique": "a critique of the design",
}


def question_out(question: models.QuizQuestion, now: datetime) -> QuizQuestion:
    practice = question.quiz.mode == "practice"
    return QuizQuestion(
        id=question.id,
        order=question.order,
        type=question.type,
        category=question.category,
        prompt=question.prompt,
        code_snippet=CodeSnippet(**question.code_snippet) if question.code_snippet else None,
        options=[QuizOption(**o) for o in question.options],
        hint=question.hint if practice else None,  # hints are for practice only
        time_limit_s=question.time_limit_s,
        served_at=question.served_at,
        time_remaining_s=time_remaining_s(question, now),
        answered=question.answer is not None,
        skill_ids=list(question.skill_ids),
    )


def visible_questions(quiz: models.Quiz, *, started: bool) -> list[models.QuizQuestion]:
    """Practice and submitted quizzes show everything. A verify quiz in progress shows what was answered
    plus the current question, and nothing at all until the student starts (`started`)."""
    if quiz.mode == "practice" or quiz.status == "submitted":
        return list(quiz.questions)
    if not started:
        return []
    current = current_question(quiz)
    return [q for q in quiz.questions if q.answer is not None or q is current]


def quiz_out(quiz: models.Quiz, now: datetime, *, started: bool = True) -> Quiz:
    return Quiz(
        id=quiz.id,
        analysis_id=quiz.analysis_id,
        project_id=quiz.project_id,
        project_title=quiz.project_title,
        mode=quiz.mode,
        status=quiz.status,
        total_questions=len(quiz.questions),
        questions=[question_out(q, now) for q in visible_questions(quiz, started=started)],
        created_at=quiz.created_at,
    )


def summary_out(quiz: models.Quiz) -> QuizSummary:
    return QuizSummary(
        id=quiz.id,
        project_id=quiz.project_id,
        project_title=quiz.project_title,
        mode=quiz.mode,
        status=quiz.status,
        score=quiz.score,
        understanding=quiz.understanding,
        created_at=quiz.created_at,
    )


def recorded(answer: models.QuizAnswer | None) -> bool:
    return answer is not None and (
        bool(answer.choice_id) or bool((answer.text or "").strip()) or answer.timed_out
    )


def feedback_out(question: models.QuizQuestion, *, reveal: bool) -> QuizAnswerFeedback:
    answer = question.answer
    base = {
        "question_id": question.id,
        "recorded": recorded(answer),
        "timed_out": bool(answer and answer.timed_out),
        "choice_id": answer.choice_id if answer else None,
        "text": answer.text if answer else None,
    }
    if not reveal:
        return QuizAnswerFeedback(**base)
    ref = question.source_ref
    return QuizAnswerFeedback(
        **base,
        score=answer.score if answer else 0.0,
        correct_choice_id=question.correct_choice_id,
        key_points=[KeyPointResult(**k) for k in (answer.key_results if answer else [])],
        incorrect_statements=list(answer.incorrect_statements) if answer else [],
        feedback=answer.feedback if answer else None,
        model_answer=question.model_answer,
        source_ref=SourceRef(**ref) if ref else None,
    )


def topic_text(question: models.QuizQuestion) -> str:
    """What to review for a question: its first missing (else partial) key point, else the model answer."""
    answer = question.answer
    for wanted in ("missing", "partial"):
        for point in answer.key_results if answer else []:
            if point["status"] == wanted:
                return point["text"]
    if question.model_answer:
        return question.model_answer.split(". ")[0].rstrip(".")[:140]
    return CATEGORY_TOPIC.get(question.category, question.category)
