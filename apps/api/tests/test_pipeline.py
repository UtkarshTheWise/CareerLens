"""The analysis pipeline and its endpoints, end to end and offline.

GitHub is replayed from the recorded UtkarshTheWise profile, the LLM is a scripted fake and the
portfolio page fetcher is a stub, so the whole job runs through the real code with no network.
"""

import re
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import catalogue
from app.config import Settings
from app.db import models
from app.db.base import SessionLocal
from app.deps import DEV_SUBJECT, get_analysis_for
from app.errors import ApiError
from app.main import app
from app.routers.analyses import get_pipeline_deps
from app.schemas.api import AnalysisReport
from app.services import scoring
from app.services.github import GitHubClient
from app.services.llm import ProviderUnavailable
from app.services.pipeline import INTERRUPTED, PipelineDeps, recover_interrupted
from app.services.portfolio import PageText
from app.services.scoring_inputs import ScoringInputs
from scripts.github_fixtures import FIXTURE_ROOT, ReplayTransport
from tests.conftest import assert_error_shape
from tests.llm_fakes import SchemaProvider, design_judgement, project_judgement

FIXTURES = Path(__file__).parent / "fixtures"
STAGES = [
    ("ingesting", 10), ("extracting", 25), ("collecting", 40), ("detecting", 55),
    ("judging", 70), ("scoring", 85), ("planning", 92), ("done", 100),
]  # fmt: skip
RESOURCE_URLS = {r.url for r in catalogue.load_resources()}

RESUME = {
    "headline": None,
    "education": [{"institution": "Example Institute", "degree": "B.Tech"}],
    "skills": ["Python", "JavaScript", "React", "Docker", "SQL", "Communication"],
    "experience": [
        {
            "org": "Example Club", "role": "Web Lead", "start": None, "end": None,
            "bullets": ["Cut page load time by 30% using React", "Ran weekly sessions"],
            "mentioned_technologies": ["React"],
        }
    ],
    "projects": [
        {
            "title": "SABTA",
            "description": "A clothing segmentation project in Python using PyTorch and Redis caching.",
            "links": [],
            "mentioned_technologies": ["Python", "PyTorch", "Redis"],
        },
        {
            "title": "Task manager",
            "description": "A personal task manager built with Node.js and Express.",
            "links": ["[URL_9]"],
            "mentioned_technologies": ["Node.js", "Express"],
        },
    ],
    "certifications": [],
    "page_count_hint": None,
}  # fmt: skip


def judge_reply(user: str):
    if "Redis caching" in user:  # SABTA: vague, and claims Redis that no detector finds
        return project_judgement(specificity=1, has_metric=False, unsupported_claims=["Redis"])
    return project_judgement()


def plan_reply(user: str):
    gaps = re.findall(r"^(gap-[a-z0-9-]+) \|", user, re.MULTILINE)[:3]
    flags = re.findall(r"^(flag-[a-z0-9-]+) \|", user, re.MULTILINE)[:2]
    catalogue_ids = re.findall(r"^([a-z0-9-]+) \| [a-z0-9-]+ \| .+ \| \w+ \| \S+$", user, re.MULTILINE)[:2]
    ms = [
        {"title": f"Milestone {i}", "deliverable": "A repository that shows it", "addresses": [a],
         "resource_ids": catalogue_ids[:1], "effort_hours": 3 + i}
        for i, a in enumerate(gaps + flags)
    ]  # fmt: skip
    return {"milestones": ms}


PAGE = PageText(
    url="https://portfolio.example.dev/work", readable=True, title="Transit app", text="Research notes. " * 30
)


class Env:
    """Fakes for everything the pipeline reaches outside the process."""

    def __init__(self, replies=None, page=PAGE, github=None):
        self.provider = SchemaProvider(
            {
                "ResumeProfile": RESUME,
                "ProjectJudgement": judge_reply,
                "DesignJudgement": design_judgement(),
                "RoadmapPlan": plan_reply,
                **(replies or {}),
            }
        )
        self.transport = ReplayTransport(FIXTURE_ROOT / "UtkarshTheWise")
        self.stages: list[tuple[str, int]] = []
        self.page, self.page_calls = page, []
        self.github = github
        self.deps = PipelineDeps(
            providers=[self.provider],
            github_client=self._github,
            fetch_page=self._page,
            on_stage=lambda status, progress: self.stages.append((status, progress)),
            today=date(2026, 10, 7),
        )

    def _github(self, db, refresh):
        if self.github is not None:
            return self.github(db, refresh)
        settings = Settings(_env_file=None, github_token="not-a-real-token")
        return GitHubClient(db, settings, transport=self.transport, refresh=refresh)

    def _page(self, url, db, refresh):
        self.page_calls.append(url)
        if isinstance(self.page, Exception):
            raise self.page
        return self.page


@pytest.fixture
def env():
    env = Env()
    app.dependency_overrides[get_pipeline_deps] = lambda: env.deps
    return env


def use(env: Env) -> Env:
    app.dependency_overrides[get_pipeline_deps] = lambda: env.deps
    return env


def make_profile(client, upload=True, **kw) -> str:
    body = {
        "name": "Aarav Mehta",
        "github_username": "UtkarshTheWise",
        "target_role_id": "sde-backend",
        "portfolio_urls": ["https://portfolio.example.dev/work"],
        **kw,
    }
    pid = client.post("/v1/profiles", json=body).json()["id"]
    if upload:
        pdf = (FIXTURES / "resume.pdf").read_bytes()
        client.post(
            f"/v1/profiles/{pid}/documents", data={"kind": "resume"}, files={"file": ("resume.pdf", pdf)}
        )
    return pid


def start(client, pid, role="sde-backend", **kw):
    return client.post(f"/v1/profiles/{pid}/analyses", json={"role_id": role, **kw})


def run_one(client, **profile_kw):
    pid = make_profile(client, **profile_kw)
    res = start(client, pid)
    assert res.status_code == 202, res.text
    return pid, res.json()["id"]


def fetch(client, analysis_id) -> dict:
    return client.get(f"/v1/analyses/{analysis_id}").json()


def report_of(client, analysis_id) -> AnalysisReport:
    body = fetch(client, analysis_id)
    assert body["status"] == "done", body
    return AnalysisReport.model_validate(body["report"])


# ---------------------------------------------------------------- the whole run


def test_start_returns_202_and_the_job_runs_through_every_stage(client, env):
    pid = make_profile(client)
    res = start(client, pid)
    assert res.status_code == 202
    queued = res.json()
    assert (queued["status"], queued["progress"], queued["role_id"], queued["profile_id"]) == (
        "queued",
        0,
        "sde-backend",
        pid,
    )
    assert env.stages == STAGES

    body = fetch(client, queued["id"])
    assert (body["status"], body["progress"], body["error"]) == ("done", 100, None)
    assert body["finished_at"] is not None


def test_the_report_is_complete_and_matches_the_contract(client, env):
    pid, aid = run_one(client)
    report = report_of(client, aid)
    assert report.score.confidence.value == "high"  # resume + GitHub + a readable portfolio item
    assert 0 < report.score.total <= 100 and {c.key for c in report.score.components} == set(
        scoring.COMPONENTS
    )
    assert report.claims and report.gaps and report.evidence and report.consistency is not None
    assert len(report.role_fits) == 3 and 4 <= len(report.roadmap) <= 7
    assert [m.id for m in report.roadmap] == [f"ms-{i}" for i in range(1, len(report.roadmap) + 1)]
    assert all(r.url in RESOURCE_URLS for m in report.roadmap for r in m.resources)
    assert any("not in the catalogue and were not scored: Communication" in n for n in report.notes)

    profile = client.get(f"/v1/profiles/{pid}").json()
    assert profile["latest_analysis_id"] == aid and profile["latest_score"] == report.score.total


def test_judging_covers_six_projects_and_raises_the_two_flags(client, env):
    _, aid = run_one(client)
    report = report_of(client, aid)
    assert len(env.provider.calls_for("ProjectJudgement")) == 6  # capped at six reviews
    assert len(env.provider.calls_for("DesignJudgement")) == 1

    by_title = {p.title: p for p in report.projects}
    sabta = by_title["SABTA"]
    assert {"vague_description", "claim_mismatch"} <= {
        f.code for f in sabta.flags
    }  # model and detectors agree
    assert sabta.what_it_does and sabta.honest_rewrite and sabta.issues
    assert sabta.flags[0].estimated_gain >= 0
    assert by_title["Transit app"].kind == "design" and by_title["Transit app"].self_reported
    assert by_title["Transit app"].issues  # design items get fix guidance too
    assert {"amity", "ordin20"} <= set(by_title)  # untouched forks are listed...
    assert all(f.code != "vague_description" for f in by_title["amity"].flags)  # ...but never reviewed
    assert any(f.code == "unmodified_fork" for f in by_title["amity"].flags)


def test_scoring_inputs_are_stored_so_the_score_can_be_recomputed(client, env):
    _, aid = run_one(client)
    report = report_of(client, aid)
    with SessionLocal() as db:
        row = db.get(models.Analysis, aid)
        stored = ScoringInputs.model_validate(row.signals)
        assert (row.score, row.coverage) == (report.score.total, report.coverage)
        assert row.verified_skills == sum(
            1 for c in report.claims if c.claimed and c.level.value in ("strong", "moderate")
        )
    assert scoring.score(stored).breakdown.total == report.score.total
    assert stored.skill_overrides == {} and stored.today == date(2026, 10, 7)


def test_nothing_personal_is_sent_to_a_model(client, env):
    run_one(client)
    prompts = env.provider.prompts
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", prompts)  # no email address
    assert not re.search(r"https?://", prompts)  # no link, so no profile URL either
    assert "Aarav" not in prompts and "Mehta" not in prompts
    assert "portfolio.example.dev" not in prompts


# ---------------------------------------------------------------- degradation: the analysis still finishes


@pytest.mark.parametrize(
    ("status", "code", "fragment"),
    [
        (404, "github_not_found", "was not found"),
        (429, "rate_limited", "rate limit"),
        (503, "github_not_configured", "isn't set up"),
        (502, "github_unavailable", "could not be reached"),
    ],
)
def test_github_problems_fall_back_to_a_resume_only_analysis_with_a_note(client, status, code, fragment):
    def broken(db, refresh):
        raise ApiError(status, code, "boom")

    use(Env(github=broken))
    _, aid = run_one(client)
    report = report_of(client, aid)
    assert any(fragment in n and "without GitHub" in n for n in report.notes)
    assert report.consistency is None and report.score.confidence.value == "medium"  # resume + portfolio
    with SessionLocal() as db:
        assert ScoringInputs.model_validate(db.get(models.Analysis, aid).signals).github_linked is False


def test_no_github_username_is_noted_and_skips_github(client, env):
    _, aid = run_one(client, github_username=None)
    assert any("No GitHub username" in n for n in report_of(client, aid).notes)
    assert env.transport.requests == 0


def test_one_project_review_failing_leaves_the_rest_and_a_note(client):
    def reply(user):
        if "Redis caching" in user:
            return ProviderUnavailable("down")
        return project_judgement()

    env = use(Env({"ProjectJudgement": reply}))
    _, aid = run_one(client)
    report = report_of(client, aid)
    notes = [n for n in report.notes if "could not be reviewed right now" in n]
    assert len(notes) == 1 and "SABTA" in notes[0]
    sabta = next(p for p in report.projects if p.title == "SABTA")
    assert sabta.what_it_does is None and not any(
        f.code in ("vague_description", "claim_mismatch") for f in sabta.flags
    )
    assert any(p.what_it_does for p in report.projects if p.title != "SABTA")
    assert env.stages[-1] == ("done", 100)


def test_an_unreadable_portfolio_page_counts_as_no_evidence(client):
    page = PageText(
        url="https://portfolio.example.dev/work", readable=False, reason="the page could not be reached"
    )
    env = use(Env(page=page))
    _, aid = run_one(client)
    report = report_of(client, aid)
    assert any("portfolio link could not be read" in n for n in report.notes)
    assert env.provider.calls_for("DesignJudgement") == []
    design = next(p for p in report.projects if p.kind == "design")
    assert design.score == 0


def test_roadmap_planner_failure_does_not_fail_the_analysis(client):
    use(Env({"RoadmapPlan": ProviderUnavailable("down")}))
    _, aid = run_one(client)
    report = report_of(client, aid)
    assert len(report.roadmap) >= 4 and any("AI planner was unavailable" in n for n in report.notes)


def test_a_resume_that_cannot_be_read_fails_with_a_clean_message(client):
    env = use(Env({"ResumeProfile": ProviderUnavailable("down")}))
    pid, aid = run_one(client)
    body = fetch(client, aid)
    assert body["status"] == "failed" and body["report"] is None
    assert "unreachable" in body["error"] or "rate-limited" in body["error"]
    assert "Traceback" not in body["error"] and env.stages[-1][0] == "extracting"
    assert client.get(f"/v1/profiles/{pid}").json()["latest_analysis_id"] is None


def test_an_unexpected_crash_is_reported_without_internals(client):
    use(Env(page=RuntimeError("secret internal detail")))
    _, aid = run_one(client)
    body = fetch(client, aid)
    assert (
        body["status"] == "failed" and body["error"] == "The analysis failed unexpectedly. Please try again."
    )
    assert "secret" not in str(body)


# ---------------------------------------------------------------- start validation


def test_start_rejects_missing_resume_unknown_role_and_unknown_profile(client, env):
    no_resume = make_profile(client, upload=False)
    res = start(client, no_resume)
    assert (res.status_code, res.json()["code"]) == (409, "no_resume")
    assert_error_shape(res.json())

    ok = make_profile(client)
    bad_role = start(client, ok, role="astronaut")
    assert bad_role.status_code == 422 and bad_role.json()["details"] == {"field": "role_id"}

    assert start(client, "00000000-0000-4000-8000-000000000000").status_code == 404
    assert env.stages == []  # nothing was queued for any of them
    with SessionLocal() as db:
        assert db.query(models.Analysis).count() == 0


# ---------------------------------------------------------------- reading analyses


def test_history_is_newest_first_with_summary_fields(client, env):
    pid = make_profile(client)
    first, second = start(client, pid).json()["id"], start(client, pid, role="full-stack").json()["id"]
    history = client.get(f"/v1/profiles/{pid}/analyses").json()
    assert [h["id"] for h in history] == [second, first]
    assert history[0]["role_id"] == "full-stack" and history[0]["status"] == "done"
    assert (
        set(history[0]) >= {"score", "coverage", "verified_skills", "created_at"} and history[0]["score"] > 0
    )


def test_a_running_analysis_shows_status_and_no_report(client):
    pid = make_profile(client)
    with SessionLocal() as db:
        row = models.Analysis(profile_id=pid, role_id="sde-backend", status="judging", progress=70)
        db.add(row)
        db.commit()
        aid = row.id
    body = fetch(client, aid)
    assert (body["status"], body["progress"], body["report"]) == ("judging", 70, None)
    assert client.get("/v1/analyses/00000000-0000-4000-8000-000000000000").status_code == 404


def test_only_the_owner_sees_an_analysis():
    with SessionLocal() as db:
        owner = models.Profile(name="Owner", auth_subject="user-1")
        db.add(owner)
        db.commit()
        row = models.Analysis(profile_id=owner.id, role_id="sde-backend")
        db.add(row)
        db.commit()
        aid = row.id
        assert get_analysis_for(aid, "user-1", db).id == aid
        assert get_analysis_for(aid, DEV_SUBJECT, db).id == aid  # DEV_AUTH sees everything
        with pytest.raises(ApiError) as exc:
            get_analysis_for(aid, "user-2", db)
        assert exc.value.status_code == 404


# ---------------------------------------------------------------- simulate and milestones


def test_simulate_runs_on_the_stored_inputs(client, env):
    _, aid = run_one(client)
    report = report_of(client, aid)
    code = next(
        p for p in report.projects if p.kind == "code" and p.counted_in_score and p.signals.tests is False
    )
    body = {"changes": [{"project_id": code.project_id, "add_signals": ["tests", "ci"]}]}
    res = client.post(f"/v1/analyses/{aid}/simulate", json=body)
    assert res.status_code == 200
    result = res.json()
    assert result["before"]["total"] == report.score.total
    assert (
        result["delta"] == pytest.approx(result["after"]["total"] - result["before"]["total"], abs=0.05)
        and result["delta"] > 0
    )
    calls_before = len(env.provider.calls)
    client.post(f"/v1/analyses/{aid}/simulate", json=body)
    assert len(env.provider.calls) == calls_before  # no LLM, and the GitHub replay was not touched either


def test_simulate_errors(client, env):
    _, aid = run_one(client)
    bad = client.post(
        f"/v1/analyses/{aid}/simulate",
        json={"changes": [{"project_id": "proj-nope", "add_signals": ["tests"]}]},
    )
    assert bad.status_code == 422 and bad.json()["code"] == "validation_error"
    assert_error_shape(bad.json())

    pid = make_profile(client)
    with SessionLocal() as db:
        row = models.Analysis(profile_id=pid, role_id="sde-backend", status="queued")
        db.add(row)
        db.commit()
        waiting = row.id
    res = client.post(f"/v1/analyses/{waiting}/simulate", json={"changes": []})
    assert (res.status_code, res.json()["code"]) == (409, "analysis_not_ready")
    assert (
        client.post(
            "/v1/analyses/00000000-0000-4000-8000-000000000000/simulate", json={"changes": []}
        ).status_code
        == 404
    )


def test_milestones_can_be_ticked_and_unticked(client, env):
    _, aid = run_one(client)
    first = report_of(client, aid).roadmap[0]
    assert first.done is False
    res = client.patch(f"/v1/analyses/{aid}/roadmap/{first.id}", json={"done": True})
    assert res.status_code == 200 and res.json()["done"] is True and res.json()["id"] == first.id
    assert report_of(client, aid).roadmap[0].done is True  # persisted in the stored report
    assert (
        client.patch(f"/v1/analyses/{aid}/roadmap/{first.id}", json={"done": False}).json()["done"] is False
    )
    assert report_of(client, aid).roadmap[0].done is False

    missing = client.patch(f"/v1/analyses/{aid}/roadmap/ms-99", json={"done": True})
    assert (missing.status_code, missing.json()["code"]) == (404, "not_found")
    assert client.patch(f"/v1/analyses/{aid}/roadmap/ms-1", json={}).status_code == 422


# ---------------------------------------------------------------- caches, refresh and restarts


def test_a_second_run_is_served_from_caches_unless_refresh_is_forced(client, env):
    pid = make_profile(client)
    start(client, pid)
    llm_calls, http_calls = len(env.provider.calls), env.transport.requests
    assert llm_calls > 0 and http_calls > 0

    start(client, pid)
    assert (len(env.provider.calls), env.transport.requests) == (llm_calls, http_calls)  # all cached

    start(client, pid, force_refresh=True)
    assert len(env.provider.calls) > llm_calls and env.transport.requests > http_calls  # both bypassed


def test_interrupted_analyses_are_failed_at_startup(client):
    pid = make_profile(client)
    with SessionLocal() as db:
        rows = [
            models.Analysis(profile_id=pid, role_id="sde-backend", status=s)
            for s in ("queued", "judging", "done", "failed")
        ]
        db.add_all(rows)
        db.commit()
        done_id = rows[2].id
    assert_state = lambda: {a.status for a in SessionLocal().query(models.Analysis).all()}  # noqa: E731
    with TestClient(app):  # entering the context runs the lifespan, which recovers stuck jobs
        pass
    assert assert_state() == {"done", "failed"}
    with SessionLocal() as db:
        stuck = [a for a in db.query(models.Analysis).all() if a.error == INTERRUPTED]
        assert len(stuck) == 2 and all(a.finished_at is not None for a in stuck)
        assert db.get(models.Analysis, done_id).status == "done"
        assert recover_interrupted(db) == 0  # idempotent


def test_run_analysis_ignores_a_vanished_row():
    from app.services.pipeline import run_analysis

    run_analysis("00000000-0000-4000-8000-000000000000", PipelineDeps())  # must not raise


def test_the_clock_is_only_read_when_no_date_is_injected(client, env):
    env.deps.today = None
    _, aid = run_one(client)
    with SessionLocal() as db:
        stored = ScoringInputs.model_validate(db.get(models.Analysis, aid).signals)
    assert stored.today == datetime.now(UTC).date()
