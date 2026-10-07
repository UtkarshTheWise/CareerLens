import json

import pytest

from app.db import models
from app.db.base import SessionLocal
from app.schemas.api import AnalysisReport, Understanding
from app.services.analysis_inputs import carry_understanding
from tests.llm_fakes import SchemaProvider
from tests.quiz_helpers import (
    PROJECT,
    REPO_URL,
    full_verify_reply,
    grading_reply,
    inputs_with_repo,
    new_env,
)
from tests.scoring_helpers import code_project, sig


def moderate_inputs():
    """campus-api with a minority of the commits: its skills are `moderate` until a quiz upgrades them."""
    project = code_project(
        "campus-api",
        skills=["python", "sql", "docker"],
        claimed_skill_ids=["python", "sql"],
        signals=sig(authored_commits=3, total_commits=10, authored_share=0.3),
    )
    return inputs_with_repo().model_copy(update={"projects": [project]})


@pytest.fixture
def env(client):
    provider = SchemaProvider({"GeneratedQuiz": full_verify_reply(), "QuizGrading": grading_reply()})
    return new_env(client, provider, inputs=moderate_inputs(), with_report=True)


def stored(env) -> tuple[AnalysisReport, models.Profile]:
    with SessionLocal() as db:
        analysis = db.get(models.Analysis, env.analysis_id)
        return AnalysisReport.model_validate(analysis.report), analysis.profile


def project_of(report: AnalysisReport):
    return next(p for p in report.projects if p.project_id == PROJECT)


def claim_level(report: AnalysisReport, skill: str) -> str:
    return next(c.level.value for c in report.claims if c.skill_id == skill)


def run_verify(env, status: str) -> dict:
    env.provider.replies["QuizGrading"] = grading_reply(status)
    quiz_id = env.create().json()["id"]
    questions = env.questions(quiz_id)
    for q in questions:
        env.get(quiz_id)
        if q["type"] == "mcq":
            wrong = next(o for o in "abcd" if o != q["correct"])
            kw = {"choice_id": q["correct"] if status == "covered" else wrong}
        else:
            kw = {"text": "An answer"}
        env.answer(quiz_id, q["id"], **kw)
    res = env.submit(quiz_id)
    assert res.status_code == 200, res.text
    return res.json()


# ---------------------------------------------------------------- demonstrated


def test_demonstrated_upgrades_covered_skills_and_raises_the_score(env):
    before, _ = stored(env)
    assert claim_level(before, "python") == "moderate" and claim_level(before, "docker") == "moderate"
    result = run_verify(env, "covered")
    assert result["understanding"] == "demonstrated" and result["flag"] is None
    update = result["score_update"]
    assert update["before"]["total"] == before.score.total
    assert update["delta"] == round(update["after"]["total"] - update["before"]["total"], 1) > 0

    after, profile = stored(env)
    assert after.score.total == update["after"]["total"]  # the report now shows the new score
    assert claim_level(after, "python") == "strong" and claim_level(after, "sql") == "strong"
    assert claim_level(after, "docker") == "moderate"  # not covered by the questions: unchanged
    audit = project_of(after)
    assert (
        audit.understanding == Understanding.demonstrated and str(audit.latest_quiz_id) == result["quiz_id"]
    )
    assert profile.latest_score == after.score.total


def test_the_result_is_carried_into_the_next_analysis(env):
    run_verify(env, "covered")
    _, profile = stored(env)
    entry = profile.project_understanding[REPO_URL]
    assert entry["understanding"] == "demonstrated" and set(entry["covered_skill_ids"]) == {"python", "sql"}
    understanding, covered, quiz_id = carry_understanding(REPO_URL, profile.project_understanding)
    assert understanding == Understanding.demonstrated and set(covered) == {"python", "sql"} and quiz_id


# ---------------------------------------------------------------- not demonstrated


def test_not_demonstrated_raises_a_fair_flag_lowers_the_score_and_adds_a_milestone(env):
    before, _ = stored(env)
    result = run_verify(env, "missing")
    assert result["understanding"] == "not_demonstrated"
    flag = result["flag"]
    assert flag["code"] == "understanding_gap" and flag["estimated_gain"] > 0
    assert flag["reason"].startswith("Your answers didn't yet cover") and "Review" in flag["fix"]
    assert "app/db.py" in flag["fix"] or "main.py" in flag["fix"]
    text = json.dumps(result).lower()
    assert "didn't build" not in text and "did not build" not in text and "fake" not in text
    assert result["score_update"]["delta"] < 0

    after, _ = stored(env)
    audit = project_of(after)
    assert audit.understanding == Understanding.not_demonstrated
    assert [f.code for f in audit.flags].count("understanding_gap") == 1
    assert claim_level(after, "python") == "weak"  # the only evidence was this project: one level down
    assert any(
        f"flag-{PROJECT.removeprefix('proj-')}-understanding-gap" in m.addresses for m in after.roadmap
    )
    assert after.score.total < before.score.total


def test_a_retake_that_shows_understanding_gives_it_back(env):
    before, _ = stored(env)
    run_verify(env, "missing")
    env.clock.advance(61 * 60)
    result = run_verify(env, "covered")
    assert result["understanding"] == "demonstrated" and result["flag"] is None
    after, profile = stored(env)
    assert "understanding_gap" not in [f.code for f in project_of(after).flags]
    assert after.score.total > before.score.total  # symmetric: the bonus, with the gap gone
    assert profile.project_understanding[REPO_URL]["understanding"] == "demonstrated"
    assert all("understanding-gap" not in a for m in after.roadmap for a in m.addresses)


# ---------------------------------------------------------------- partial, practice, abandoned


def test_partial_changes_no_levels_and_no_points(env):
    before, _ = stored(env)
    result = run_verify(env, "partial")
    assert result["understanding"] == "partial" and result["flag"] is None
    assert result["score_update"]["delta"] == 0.0
    after, _ = stored(env)
    assert [c.level for c in after.claims] == [c.level for c in before.claims]
    assert project_of(after).understanding == Understanding.partial


def test_practice_and_abandoned_quizzes_leave_the_report_alone(env):
    with SessionLocal() as db:
        original = db.get(models.Analysis, env.analysis_id).report
    practice = env.create("practice").json()["id"]
    env.submit(practice)
    verify = env.create().json()["id"]
    env.clock.advance(31 * 60)
    env.get(verify)  # auto-closed as abandoned
    with SessionLocal() as db:
        analysis = db.get(models.Analysis, env.analysis_id)
        assert analysis.report == original and analysis.profile.project_understanding == {}


def test_an_auto_submitted_quiz_is_scored_like_any_other_verify_result(env):
    quiz_id = env.create().json()["id"]
    env.get(quiz_id)
    env.clock.advance(60 * 60)
    assert env.get(quiz_id).json()["status"] == "submitted"
    after, _ = stored(env)
    assert project_of(after).understanding == Understanding.not_demonstrated
    assert env.result(quiz_id).json()["score_update"]["delta"] < 0


# ---------------------------------------------------------------- what stays


def test_roadmap_ticks_survive_a_replan(env):
    before, _ = stored(env)
    ticked = before.roadmap[0]
    with SessionLocal() as db:
        analysis = db.get(models.Analysis, env.analysis_id)
        report = json.loads(json.dumps(analysis.report))
        report["roadmap"][0]["done"] = True
        analysis.report = report
        db.commit()
    run_verify(env, "partial")
    after, _ = stored(env)
    same = [m for m in after.roadmap if set(m.addresses) == set(ticked.addresses)]
    assert same and all(m.done for m in same)


def test_project_text_written_by_the_model_is_kept(env):
    with SessionLocal() as db:
        analysis = db.get(models.Analysis, env.analysis_id)
        report = json.loads(json.dumps(analysis.report))
        report["projects"][0]["what_it_does"] = "A REST API for campus events."
        report["projects"][0]["honest_rewrite"] = "Built a FastAPI service."
        analysis.report = report
        db.commit()
    run_verify(env, "covered")
    audit = project_of(stored(env)[0])
    assert (
        audit.what_it_does == "A REST API for campus events."
        and audit.honest_rewrite == "Built a FastAPI service."
    )


def test_the_cohort_view_sees_the_status_and_nothing_else(env, client):
    run_verify(env, "covered")
    with SessionLocal() as db:
        cohort = models.Cohort(name="Test cohort")
        db.add(cohort)
        db.flush()
        db.get(models.Profile, env.profile_id).cohort_id = cohort.id
        db.commit()
        cohort_id = cohort.id
    insights = client.get(f"/v1/cohorts/{cohort_id}/insights", params={"role_id": "sde-backend"}).json()
    students = client.get(f"/v1/cohorts/{cohort_id}/students", params={"role_id": "sde-backend"}).json()
    assert insights["understanding"]["quizzed"] == 1 and insights["understanding"]["demonstrated"] == 1
    assert students[0]["understanding"] == "demonstrated"
    body = json.dumps([insights, students]).lower()
    assert "focus" not in body and "key_point" not in body and "model_answer" not in body
