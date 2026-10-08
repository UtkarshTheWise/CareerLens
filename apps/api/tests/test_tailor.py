import pytest

from app.db import models
from app.db.base import SessionLocal
from app.main import app
from app.routers.analyses import get_pipeline_deps
from app.schemas.llm import ResumeExperience, ResumeProfile, ResumeProject
from app.services import tailor
from app.services.llm import ProviderUnavailable
from tests.conftest import assert_error_shape
from tests.llm_fakes import SchemaProvider
from tests.quiz_helpers import FakeGitHub, deps, inputs_with_repo, make_analysis

JOB = (
    "We build REST APIs in Python (FastAPI) on SQL databases, packaged with Docker. Redis caching is a plus."
)
B1 = "Reduced API response time by 35% by adding Redis caching to two endpoints"


def resume(**kw) -> ResumeProfile:
    base = {
        "experience": [
            ResumeExperience(
                org="Northwind Labs",
                role="Backend Intern",
                bullets=[B1, "Documented the deployment steps for interns"],
            )
        ],
        "projects": [
            ResumeProject(
                title="campus-api",
                description="REST API for campus events built with FastAPI and SQL. Handled 10,000 requests in 20 commits.",
            )
        ],
    }
    return ResumeProfile(**{**base, **kw})


def draft(*bullets: dict) -> dict:
    return {"bullets": list(bullets)}


def rewrite(n: int, text: str, evidence=()) -> dict:
    return {"bullet_id": f"b{n}", "rewritten": text, "evidence_ids": list(evidence)}


@pytest.fixture
def setup(client):
    """(application id, provider) for a profile with a finished analysis and a job description."""

    def make(reply, *, resume_profile=None, description=JOB, with_analysis=True):
        provider = SchemaProvider({"TailoredDraft": reply})
        app.dependency_overrides[get_pipeline_deps] = lambda: deps(provider, FakeGitHub())
        inputs = inputs_with_repo().model_copy(update={"resume": resume_profile or resume()})
        with SessionLocal() as db:
            analysis = make_analysis(db, inputs, with_report=with_analysis)
            application = models.Application(
                profile_id=analysis.profile_id, company="Northwind Labs", title="Backend Engineer Intern",
                description=description,
            )  # fmt: skip
            db.add(application)
            db.commit()
            return application.id, provider

    return make


def call(client, application_id: str):
    return client.post(f"/v1/applications/{application_id}/tailored-resume")


# ---------------------------------------------------------------- pure helpers


def test_numbers_in_ignores_years_and_keeps_metrics():
    assert tailor.numbers_in("Cut latency by 35% in 2025, serving 10,000 users, 3.5x faster, 12 weeks") == [
        "35%", "10,000", "3.5", "12",
    ]  # fmt: skip


def test_check_rewrite_keeps_safe_rewrites_and_falls_back_otherwise():
    allowed = {"python", "redis"}
    assert tailor.check_rewrite(
        B1, "Cut API response time 35% with Redis caching on two endpoints", allowed
    ).startswith("Cut API")
    assert (
        tailor.check_rewrite(B1, "Cut API response time by 50% with Redis caching", allowed) == B1
    )  # new number
    assert (
        tailor.check_rewrite(B1, "Cut API response time 35% using Redis and Kubernetes", allowed) == B1
    )  # unverified skill
    assert (
        tailor.check_rewrite(B1, "   ", allowed) == B1 and tailor.check_rewrite(B1, "x" * 500, allowed) == B1
    )
    keep = "Documented Docker deployment steps"
    assert (
        tailor.check_rewrite("Wrote Docker deployment steps", keep, set()) == keep
    )  # skill was already in the original


# ---------------------------------------------------------------- the endpoint


def test_a_safe_rewrite_is_kept_with_only_real_evidence_ids(client, setup):
    app_id, provider = setup(
        draft(
            rewrite(
                1,
                "Cut API response time 35% by adding Redis caching to two endpoints",
                ["ev-exp-1", "ev-invented"],
            )
        )
    )
    res = call(client, app_id)
    assert res.status_code == 200, res.text
    body = res.json()
    first = body["bullets"][0]
    assert first["original"] == B1 and first["rewritten"].startswith("Cut API response time 35%")
    assert first["evidence_ids"] == ["ev-exp-1"]  # the invented id is dropped
    assert set(body) == {"bullets", "numbers_without_evidence", "skills_order"}


def test_an_invented_skill_or_number_keeps_the_original_bullet(client, setup):
    reply = draft(
        rewrite(1, "Cut response time 35% with Redis and Kubernetes on AWS", ["ev-exp-1"]),
        rewrite(2, "Documented deployment steps, saving interns 20 hours a week"),
    )
    app_id, _ = setup(reply)
    bullets = call(client, app_id).json()["bullets"]
    assert bullets[0]["rewritten"] == B1 and bullets[0]["evidence_ids"] == []
    assert bullets[1]["rewritten"] == bullets[1]["original"]


def test_missing_and_unknown_bullet_ids_leave_bullets_unchanged_and_in_order(client, setup):
    app_id, _ = setup(draft(rewrite(9, "Something about a bullet that does not exist")))
    bullets = call(client, app_id).json()["bullets"]
    assert [b["original"] for b in bullets][:2] == [B1, "Documented the deployment steps for interns"]
    assert len(bullets) == 3 and all(b["rewritten"] == b["original"] for b in bullets)


def test_originals_always_come_from_the_stored_resume(client, setup):
    reply = {
        "bullets": [
            {
                "bullet_id": "b1",
                "rewritten": "Cut API response time 35% with Redis caching",
                "evidence_ids": [],
                "original": "FORGED",
            }
        ]
    }
    app_id, _ = setup(reply)
    assert call(client, app_id).json()["bullets"][0]["original"] == B1


def test_numbers_without_supporting_facts_are_listed_not_removed(client, setup):
    app_id, _ = setup(draft())
    body = call(client, app_id).json()
    assert body["numbers_without_evidence"] == [
        "35%",
        "10,000",
    ]  # "20 commits" is backed by the repository facts
    assert "10,000 requests" in body["bullets"][2]["original"]  # the bullet itself is untouched


def test_skills_order_puts_the_jobs_verified_skills_first_and_leaves_out_unverified_ones(client, setup):
    app_id, _ = setup(draft())
    order = call(client, app_id).json()["skills_order"]
    # the job names Python, FastAPI, SQL, Docker and Redis; the student has verified Docker, Python, SQL
    # (strong, so first, by name) and Redis (moderate, so after them); the rest follow
    assert order[:4] == ["Docker", "Python", "SQL", "Redis"]
    assert "FastAPI" not in order and "Kubernetes" not in order and "AWS" not in order  # not verified
    assert len(order) == len(set(order))


def test_unverified_skills_are_not_among_the_facts_the_model_is_given(client, setup):
    app_id, provider = setup(draft())
    call(client, app_id)
    user = provider.calls_for("TailoredDraft")[0]["user"]
    facts = user.split("VERIFIED_FACTS")[1].split("BULLETS:")[0]
    assert "Python (strong)" in facts and "Kubernetes" not in facts and "AWS" not in facts
    assert provider.calls_for("TailoredDraft")[0]["model"] == "fake-smart"


def test_contact_details_are_stripped_from_the_prompt_and_restored_in_the_result(client, setup):
    note = "Built a portal, see https://github.com/u/campus-api or mail priya@example.com"
    rp = resume(experience=[ResumeExperience(org="X", role="Intern", bullets=[note])], projects=[])
    app_id, provider = setup(
        draft(rewrite(1, "Built a portal; code at [URL_1], contact [EMAIL_1]")), resume_profile=rp
    )
    prompt = provider.calls_for("TailoredDraft")
    body = call(client, app_id).json()
    sent = provider.calls_for("TailoredDraft")[0]["user"]
    assert "priya@example.com" not in sent and "github.com/u/campus-api" not in sent and "Priya" not in sent
    assert "https://github.com/u/campus-api" in body["bullets"][0]["original"]
    assert prompt is not None


def test_no_bullets_still_returns_the_skills_order_without_calling_the_model(client, setup):
    app_id, provider = setup(draft(), resume_profile=ResumeProfile())
    body = call(client, app_id).json()
    assert body["bullets"] == [] and body["skills_order"] and provider.calls == []


# ---------------------------------------------------------------- refusals


def test_needs_a_finished_analysis_and_a_job_description(client, setup):
    no_analysis, _ = setup(draft(), with_analysis=False)
    res = call(client, no_analysis)
    assert res.status_code == 409 and res.json()["code"] == "no_analysis"
    short, _ = setup(draft(), description="Backend role")
    res = call(client, short)
    assert res.status_code == 422 and res.json()["code"] == "no_description"
    assert_error_shape(res.json())


def test_unknown_application_is_404(client, setup):
    setup(draft())
    res = call(client, "00000000-0000-4000-8000-000000000000")
    assert res.status_code == 404
    assert_error_shape(res.json())


def test_an_llm_outage_is_a_429_not_an_unchanged_resume(client, setup):
    app_id, _ = setup(ProviderUnavailable("busy"))
    res = call(client, app_id)
    assert res.status_code == 429 and res.json()["code"] == "llm_unavailable"
