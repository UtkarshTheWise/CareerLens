import pytest

from app.db import models
from app.schemas.api import Understanding
from app.services.quiz_grading import (
    grade_mcq,
    grade_without_answer,
    has_answer,
    quiz_score,
    short_answer_score,
    understanding_for,
)


def test_short_answer_score_counts_partial_as_half():
    assert short_answer_score(["covered", "covered", "covered"], 0) == 1.0
    assert short_answer_score(["covered", "partial", "missing"], 0) == 0.5
    assert short_answer_score(["covered", "covered", "missing", "missing"], 0) == 0.5
    assert short_answer_score(["missing", "missing", "missing"], 0) == 0.0


def test_each_incorrect_statement_costs_a_quarter_and_the_score_is_clamped():
    assert short_answer_score(["covered", "covered", "covered"], 1) == 0.75
    assert short_answer_score(["covered", "partial", "missing"], 1) == 0.25
    assert short_answer_score(["covered", "partial", "missing"], 2) == 0.0  # clamped at 0
    assert short_answer_score(["covered", "covered", "covered"], 0) <= 1.0
    assert short_answer_score([], 0) == 0.0


def test_quiz_score_weights_short_answers_double():
    # four short answers fully right, two MCQ wrong: 8 of 10 weight points
    assert quiz_score([("mcq", 0), ("mcq", 0)] + [("short_answer", 1)] * 4) == 80.0
    # two MCQ right, four short answers wrong: 2 of 10
    assert quiz_score([("mcq", 1), ("mcq", 1)] + [("short_answer", 0)] * 4) == 20.0
    assert quiz_score([("mcq", 1)]) == 100.0
    assert quiz_score([("short_answer", 0.5), ("mcq", 1)]) == pytest.approx(66.7, abs=0.05)
    assert quiz_score([]) == 0.0


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100, Understanding.demonstrated),
        (70, Understanding.demonstrated),
        (69.9, Understanding.partial),
        (40, Understanding.partial),
        (39.9, Understanding.not_demonstrated),
        (0, Understanding.not_demonstrated),
    ],
)
def test_understanding_thresholds(score, expected):
    assert understanding_for(score) == expected


def question(**kw) -> models.QuizQuestion:
    base = {
        "id": "q1", "type": "mcq", "prompt": "p", "options": [{"id": "a", "text": "Yes"}, {"id": "b", "text": "No"}],
        "correct_choice_id": "a", "key_points": ["one", "two", "three"], "source_ref": {"path": "main.py"},
        "model_answer": "Because it is.",
    }  # fmt: skip
    return models.QuizQuestion(**{**base, **kw})


def test_mcq_is_all_or_nothing_and_a_late_choice_counts_for_nothing():
    q = question()
    right = models.QuizAnswer(choice_id="a")
    grade_mcq(q, right)
    assert right.score == 1.0 and right.feedback.startswith("That's right")
    wrong = models.QuizAnswer(choice_id="b")
    grade_mcq(q, wrong)
    assert wrong.score == 0.0 and '"Yes"' in wrong.feedback and "main.py" in wrong.feedback
    late = models.QuizAnswer(choice_id="a", timed_out=True)
    grade_mcq(q, late)
    assert late.score == 0.0 and "Time ran out" in late.feedback
    none = models.QuizAnswer()
    grade_mcq(q, none)
    assert none.score == 0.0


def test_unanswered_short_answer_shows_every_key_point_as_missing():
    q = question(type="short_answer")
    answer = models.QuizAnswer()
    grade_without_answer(q, answer)
    assert answer.score == 0.0 and [k["status"] for k in answer.key_results] == ["missing"] * 3


def test_what_counts_as_an_answer():
    assert has_answer(models.QuizAnswer(choice_id="a")) and has_answer(models.QuizAnswer(text=" x "))
    assert not has_answer(None) and not has_answer(models.QuizAnswer(text="   "))
    assert not has_answer(models.QuizAnswer(text="late", timed_out=True))
