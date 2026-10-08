"""Grading (docs/QUIZ.md section 3). The model only classifies key points; Python computes every number.

q_score  = (covered + 0.5 x partial) / key_points - 0.25 x incorrect_statements   (clamped to 0-1)
MCQ      = 1 if the choice is the key, else 0
quiz     = 100 x sum(w x q_score) / sum(w)        w = 1 for MCQ, 2 for short answer
>= 70 demonstrated, >= 40 partial, below that not_demonstrated
"""

import logging

from sqlalchemy.orm import Session

from app.db import models
from app.prompts import load_prompt
from app.schemas.api import Understanding
from app.schemas.llm import GradedAnswer, QuizGrading
from app.services.ingest import restore_pii, strip_pii
from app.services.llm import LLMError, Provider, Tier, generate_structured

logger = logging.getLogger("careerlens.quiz")

DEMONSTRATED_MIN = 70.0
PARTIAL_MIN = 40.0
WEIGHT = {"mcq": 1, "short_answer": 2}
CREDIT = {"covered": 1.0, "partial": 0.5, "missing": 0.0}
INCORRECT_PENALTY = 0.25
MAX_ANSWER_CHARS = 2_000


def short_answer_score(statuses: list[str], incorrect: int) -> float:
    """0-1 from the key-point statuses and the count of statements that contradict the code."""
    if not statuses:
        return 0.0
    raw = sum(CREDIT[s] for s in statuses) / len(statuses) - INCORRECT_PENALTY * incorrect
    return round(min(1.0, max(0.0, raw)), 3)


def quiz_score(parts: list[tuple[str, float]]) -> float:
    """0-100 from (question type, 0-1 score) pairs, weighted per the spec."""
    total = sum(WEIGHT[t] for t, _ in parts)
    if total == 0:
        return 0.0
    return round(100 * sum(WEIGHT[t] * s for t, s in parts) / total, 1)


def understanding_for(score: float) -> Understanding:
    if score >= DEMONSTRATED_MIN:
        return Understanding.demonstrated
    return Understanding.partial if score >= PARTIAL_MIN else Understanding.not_demonstrated


def has_answer(answer: models.QuizAnswer | None) -> bool:
    """Whether the student gave something gradable (a choice, or non-empty text, in time)."""
    if answer is None or answer.timed_out:
        return False
    return bool(answer.choice_id) or bool((answer.text or "").strip())


# ---------------------------------------------------------------- deterministic part


def grade_mcq(question: models.QuizQuestion, answer: models.QuizAnswer) -> None:
    right = has_answer(answer) and answer.choice_id == question.correct_choice_id
    answer.score = 1.0 if right else 0.0
    answer.key_results, answer.incorrect_statements = [], []
    answer.feedback = _mcq_feedback(question, answer, right)


def _mcq_feedback(question: models.QuizQuestion, answer: models.QuizAnswer, right: bool) -> str:
    if right:
        return "That's right. " + (question.model_answer or "")
    if answer.timed_out:
        return "Time ran out on this one. " + (question.model_answer or "")
    key = next((o["text"] for o in question.options if o["id"] == question.correct_choice_id), "")
    where = f" Review {question.source_ref['path']}." if question.source_ref else ""
    return f'Not quite: the expected answer was "{key}".{where}'


def grade_without_answer(question: models.QuizQuestion, answer: models.QuizAnswer) -> None:
    """An unanswered or timed-out short answer: 0, with the key points shown as still to cover."""
    answer.score = 0.0
    answer.key_results = [{"text": k, "status": "missing"} for k in question.key_points]
    answer.incorrect_statements = []
    answer.feedback = (
        "Time ran out on this one; the model answer shows what to review."
        if answer.timed_out
        else "No answer was given for this one; the model answer shows what to review."
    )


# ---------------------------------------------------------------- the model's part


_SEP = "\n=====FIELD=====\n"


def _item(question: models.QuizQuestion, prompt_text: str, context: str, answer_text: str) -> str:
    """One question for the grader. The three free-text fields arrive already stripped of personal details."""
    lines = [f"QUESTION_ID: {question.id}", f"Question: {prompt_text}"]
    if context:
        where = question.source_ref.get("path", "") if question.source_ref else ""
        lines.append(f"Code or page text the question is about ({where}):\n{context}")
    lines.append("Key points, in order:")
    lines += [f"{n}. {text}" for n, text in enumerate(question.key_points, start=1)]
    if question.acceptable_alternatives:
        lines.append("Acceptable alternatives: " + "; ".join(question.acceptable_alternatives))
    # The answer is the student's text and may try to give orders: it is fenced, and the system prompt says
    # that nothing inside the fence is an instruction.
    fenced = answer_text.replace("<student_answer>", "").replace("</student_answer>", "")
    lines.append(f"Student's answer:\n<student_answer>\n{fenced}\n</student_answer>")
    return "\n".join(lines)


def _stripped_items(pairs: list[tuple[models.QuizQuestion, models.QuizAnswer]]) -> tuple[str, dict[str, str]]:
    """The grader prompt body with names, emails, phones and links replaced by placeholders (AGENTS.md), and
    the mapping to put them back into the model's feedback."""
    fields = []
    for question, answer in pairs:
        fields += [
            question.prompt,
            question.grading_context or "",
            (answer.text or "").strip()[:MAX_ANSWER_CHARS],
        ]
    name = pairs[0][0].quiz.profile.name
    stripped = strip_pii(_SEP.join(fields), known_names=[name] if name else [], header_name=False)
    parts = stripped.text.split(_SEP)
    items = [_item(q, *parts[3 * n : 3 * n + 3]) for n, (q, _) in enumerate(pairs)]
    return "\n\n---\n\n".join(items), stripped.mapping


def _aligned(question: models.QuizQuestion, graded: GradedAnswer) -> bool:
    return len(graded.key_points) == len(question.key_points)


def grade_short_answers(
    db: Session,
    pairs: list[tuple[models.QuizQuestion, models.QuizAnswer]],
    *,
    tier: Tier,
    providers: list[Provider] | None,
) -> None:
    """Grade every pair in ONE call (verify: smart tier at submit; practice: fast tier, one pair).

    A reply that misses a question or a key point is asked for again once, then reported as an invalid
    response (the quiz stays open so the student can submit again) rather than scored as zero.
    """
    if not pairs:
        return
    prompt = load_prompt("quiz_grade")
    body, mapping = _stripped_items(pairs)
    user = prompt.user(items=body)
    by_id = {q.id: (q, a) for q, a in pairs}
    for attempt in (0, 1):
        result = generate_structured(
            QuizGrading,
            prompt.system,
            user,
            tier=tier,
            db=db,
            providers=providers,
            force_refresh=attempt == 1,
        )
        graded = {g.question_id: g for g in result.answers if g.question_id in by_id}
        if all(qid in graded and _aligned(by_id[qid][0], graded[qid]) for qid in by_id):
            break
        logger.warning("quiz grading reply incomplete (attempt %d)", attempt + 1)
    else:
        raise LLMError("llm_invalid_response", "The grader's reply was incomplete")

    for qid, (question, answer) in by_id.items():
        g = graded[qid]
        answer.key_results = [
            {"text": k, "status": p.status} for k, p in zip(question.key_points, g.key_points, strict=True)
        ]
        statements = [restore_pii(s, mapping) for s in g.incorrect_statements if s.strip()][:5]
        answer.incorrect_statements = statements
        answer.score = short_answer_score([p.status for p in g.key_points], len(statements))
        answer.feedback = restore_pii(g.feedback.strip(), mapping) or None
