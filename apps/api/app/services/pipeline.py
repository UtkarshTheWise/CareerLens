"""The analysis pipeline (docs/PIPELINE.md): runs stages 1-8 as a background job.

`run_analysis` opens its own DB session (the request's is closed by the time it runs), writes `status`
and `progress` after every stage so the UI can show live progress, and never lets a problem with one
source (GitHub, one project's review, one portfolio page, the roadmap planner) fail the whole analysis:
it records a note in the report and carries on with what it has. Only a missing resume or a failed
resume extraction fails it. Stage timings are logged; resume text and tokens never are.
"""

import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import catalogue
from app.db import models
from app.db.base import SessionLocal
from app.errors import ApiError
from app.schemas.api import AnalysisReport, ProjectIssue
from app.services import detectors, scoring
from app.services.analysis_inputs import (
    DesignItem,
    ProjectText,
    build_project_inputs,
    judge_design_item,
    judge_project,
    match_resume_projects,
    select_for_review,
)
from app.services.github import GitHubClient, GithubSnapshot, collect
from app.services.llm import LLMError, Provider
from app.services.planner import plan_roadmap
from app.services.portfolio import PageText, fetch_page
from app.services.resume import extract_resume
from app.services.scoring_inputs import DesignInput, ScoringInputs

logger = logging.getLogger("careerlens.pipeline")

MAX_PORTFOLIO_LINKS = 5
INTERRUPTED = "Interrupted by a server restart; start the analysis again."
_CONTACT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+|\+?\d[\d\s().-]{8,}\d")

GITHUB_NOTES = {
    "github_not_found": "That GitHub user was not found, so the analysis ran without GitHub.",
    "rate_limited": "GitHub's rate limit was reached, so the analysis ran without GitHub. Try again shortly.",
    "github_not_configured": "GitHub access isn't set up on the server, so the analysis ran without GitHub.",
    "github_auth_failed": "GitHub access isn't set up on the server, so the analysis ran without GitHub.",
    "github_unavailable": "GitHub could not be reached, so the analysis ran without GitHub.",
}


@dataclass
class PipelineDeps:
    """Everything the pipeline reaches outside the process for. Tests replace these with fakes."""

    providers: list[Provider] | None = None  # None: the configured LLM providers
    github_client: Callable[[Session, bool], GitHubClient] | None = None  # (db, refresh)
    fetch_page: Callable[[str, Session, bool], PageText] | None = None  # (url, db, refresh)
    on_stage: Callable[[str, int], None] | None = None  # called after each status write
    today: date | None = None


def _set_stage(
    db: Session, analysis: models.Analysis, deps: PipelineDeps, status: str, progress: int
) -> None:
    analysis.status, analysis.progress = status, progress
    db.commit()
    if deps.on_stage:
        deps.on_stage(status, progress)


def _fail(db: Session, analysis: models.Analysis, message: str) -> None:
    db.rollback()
    analysis.status, analysis.error = "failed", message[:500]
    analysis.finished_at = datetime.now(UTC)
    db.commit()


def recover_interrupted(db: Session) -> int:
    """At startup: analyses a restart left half-done can never finish, so mark them failed."""
    rows = db.scalars(select(models.Analysis).where(models.Analysis.status.not_in(["done", "failed"]))).all()
    for row in rows:
        row.status, row.error, row.finished_at = "failed", INTERRUPTED, datetime.now(UTC)
    db.commit()
    return len(rows)


def run_analysis(analysis_id: str, deps: PipelineDeps, force_refresh: bool = False) -> None:
    """Entry point for BackgroundTasks."""
    with SessionLocal() as db:
        analysis = db.get(models.Analysis, analysis_id)
        if analysis is None:
            return
        try:
            _run(db, analysis, deps, force_refresh)
        except (ApiError, LLMError) as exc:
            logger.warning("analysis %s failed: %s", analysis_id, getattr(exc, "code", "error"))
            _fail(db, analysis, exc.message)
        except Exception:
            logger.exception("analysis %s crashed", analysis_id)
            _fail(db, analysis, "The analysis failed unexpectedly. Please try again.")


# ---------------------------------------------------------------- the stages


def _latest_text(profile: models.Profile, kind: str) -> str:
    docs = sorted((d for d in profile.documents if d.kind == kind), key=lambda d: d.created_at)
    return docs[-1].text if docs else ""


def _collect_github(
    profile: models.Profile, db: Session, deps: PipelineDeps, refresh: bool, notes: list[str]
) -> GithubSnapshot | None:
    login = (profile.github_username or "").strip()
    if not login:
        notes.append(
            "No GitHub username was given, so project and consistency evidence come from the resume only."
        )
        return None
    try:
        factory = deps.github_client or (lambda session, fresh: GitHubClient(session, refresh=fresh))
        return collect(login, db, client=factory(db, refresh))
    except ApiError as exc:
        if exc.code not in GITHUB_NOTES:
            raise
        notes.append(GITHUB_NOTES[exc.code])
        return None


def _detect(snapshot: GithubSnapshot | None, notes: list[str]) -> dict[str, detectors.RepoAnalysis]:
    analyses: dict[str, detectors.RepoAnalysis] = {}
    for repo in snapshot.repos if snapshot else []:
        if not (repo.detailed or repo.has_commit_facts):
            continue
        try:
            analyses[repo.name] = detectors.detect(repo, snapshot.fetcher(repo.name))
        except ApiError:
            notes.append(
                f"Some files of '{repo.name}' could not be read, so it was checked from what was available."
            )
            analyses[repo.name] = detectors.detect(repo, lambda paths: {})
    return analyses


def _judge(
    profile: models.Profile,
    resume,
    role: catalogue.RoleDef,
    snapshot: GithubSnapshot | None,
    analyses: dict[str, detectors.RepoAnalysis],
    matched: dict,
    db: Session,
    deps: PipelineDeps,
    refresh: bool,
    notes: list[str],
) -> tuple[dict, list[DesignItem]]:
    judgements = {}
    repos = {r.name: r for r in snapshot.repos} if snapshot else {}
    for name in select_for_review(snapshot, analyses, matched, role) if snapshot else []:
        try:
            judgements[name] = judge_project(
                repos[name],
                analyses[name],
                matched.get(name),
                role,
                student_name=profile.name,
                db=db,
                providers=deps.providers,
                refresh=refresh,
            )
        except LLMError:
            notes.append(f"'{name}' could not be reviewed right now and was scored without that review.")

    page_fetcher = deps.fetch_page or (lambda url, session, fresh: fetch_page(url, session, refresh=fresh))
    items: list[DesignItem] = []
    for url in (profile.portfolio_urls or [])[:MAX_PORTFOLIO_LINKS]:
        page = page_fetcher(url, db, refresh)
        if not page.readable:
            notes.append(
                f"A portfolio link could not be read ({page.reason}), so it counts as having no evidence yet."
            )
        try:
            items.append(
                judge_design_item(
                    page,
                    role,
                    resume,
                    student_name=profile.name,
                    db=db,
                    providers=deps.providers,
                    refresh=refresh,
                )
            )
        except LLMError:
            notes.append(
                "A portfolio page could not be reviewed right now and was scored as having no evidence."
            )
            items.append(DesignItem(url, page, DesignInput(readable=False)))
    return judgements, items


def _with_text(projects, texts: dict[str, ProjectText]):
    out = []
    for audit in projects:
        text = texts.get(audit.project_id)
        if text is not None:
            audit = audit.model_copy(
                update={
                    "what_it_does": text.what_it_does,
                    "honest_rewrite": text.honest_rewrite,
                    "issues": [ProjectIssue(issue=i.issue, fix=i.fix) for i in text.issues],
                }
            )
        out.append(audit)
    return out


def save_report(analysis: models.Analysis, inputs: ScoringInputs, report: AnalysisReport) -> None:
    """Store a finished report with its scoring inputs and update the profile's latest score.

    Does not set `status` or commit: the pipeline does that through `_set_stage`, the seed script directly.
    """
    analysis.report = report.model_dump(mode="json")
    analysis.signals = inputs.model_dump(mode="json")
    analysis.score = report.score.total
    analysis.coverage = report.coverage
    analysis.verified_skills = sum(
        1 for c in report.claims if c.claimed and c.level.value in ("strong", "moderate")
    )
    analysis.finished_at = datetime.now(UTC)
    profile = analysis.profile
    profile.latest_analysis_id = analysis.id
    profile.latest_score = report.score.total


def _run(db: Session, analysis: models.Analysis, deps: PipelineDeps, refresh: bool) -> None:
    started = time.perf_counter()
    profile = analysis.profile
    role = catalogue.get_role(analysis.role_id)
    if role is None:
        raise ApiError(422, "validation_error", f"Unknown role '{analysis.role_id}'")
    notes: list[str] = []
    timings: dict[str, int] = {}

    def stage(status: str, progress: int) -> None:
        timings[status] = int((time.perf_counter() - started) * 1000)
        _set_stage(db, analysis, deps, status, progress)

    # 1. ingesting: texts already stored at upload; facts that need the raw text are taken here
    stage("ingesting", 10)
    raw_resume = _latest_text(profile, "resume")
    if not raw_resume:
        raise ApiError(409, "no_resume", "Upload a resume before starting an analysis")
    linkedin = "\n\n".join(t for t in (_latest_text(profile, "linkedin"), profile.linkedin_text or "") if t)
    has_contact = bool(_CONTACT.search(raw_resume))

    # 2. extracting
    stage("extracting", 25)
    resume = extract_resume(profile, db, force_refresh=refresh, providers=deps.providers)

    # 3. collecting
    stage("collecting", 40)
    snapshot = _collect_github(profile, db, deps, refresh, notes)

    # 4. detecting
    stage("detecting", 55)
    analyses = _detect(snapshot, notes)

    # 5. judging
    stage("judging", 70)
    matched = match_resume_projects(resume, snapshot.repos) if snapshot else {}
    judgements, design_items = _judge(
        profile, resume, role, snapshot, analyses, matched, db, deps, refresh, notes
    )

    # 6. scoring
    stage("scoring", 85)
    projects, texts = build_project_inputs(
        snapshot, analyses, matched, judgements, design_items, profile.project_understanding or {}
    )
    inputs = ScoringInputs(
        today=deps.today or datetime.now(UTC).date(),
        target_role_id=role.id,
        resume=resume,
        has_contact=has_contact,
        has_linkedin=bool(linkedin),
        linkedin_skill_ids=sorted(catalogue.find_skills_in_text(linkedin)),
        github_linked=snapshot is not None,
        weeks=snapshot.weeks if snapshot else [],
        last_active_date=snapshot.last_active_date if snapshot else None,
        projects=projects,
    )
    result = scoring.score(inputs)
    fits = scoring.role_fits(inputs)

    # 7. planning
    stage("planning", 92)
    roadmap, plan_notes = plan_roadmap(inputs, result, role, db, providers=deps.providers, refresh=refresh)

    # 8. persist
    report = AnalysisReport(
        score=result.breakdown,
        coverage=result.coverage,
        claims=result.claims,
        gaps=result.gaps,
        projects=_with_text(result.projects, texts),
        role_fits=fits,
        roadmap=roadmap,
        consistency=result.consistency,
        evidence=result.evidence,
        notes=notes + result.notes + plan_notes,
    )
    save_report(analysis, inputs, report)
    _set_stage(db, analysis, deps, "done", 100)
    logger.info(
        "analysis %s done score=%s ms=%d stages=%s",
        analysis.id, report.score.total, (time.perf_counter() - started) * 1000, timings,
    )  # fmt: skip
