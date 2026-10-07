"""What a verify result does to the evidence (docs/QUIZ.md section 5, SCORING.md section 6).

`apply_verify_result` sets the project's understanding on the stored scoring inputs and re-scores them (pure
`scoring.score`, no GitHub). It rebuilds the stored report so the dashboard shows the new score, claims,
flags and roadmap, keeps the project's understanding on the profile so later analyses carry it, and returns
the before/after the quiz result shows. The scoring rules themselves (strong upgrade, step-down, +/-5)
live in `scoring.py`; this module only feeds them. Practice and abandoned quizzes never come here.
"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app import catalogue
from app.db import models
from app.schemas.api import (
    AnalysisReport,
    ProjectAudit,
    ProjectFlag,
    RoadmapMilestone,
    SimulationResult,
    Understanding,
)
from app.services import scoring
from app.services.pipeline import PipelineDeps, store_report
from app.services.planner import plan_roadmap
from app.services.quiz_views import topic_text
from app.services.scoring_inputs import FlagInput, ProjectInput, ScoringInputs

logger = logging.getLogger("careerlens.quiz")

WEAK_Q = 0.7
GAP_QUESTIONS = 2  # the flag names the two weakest questions


def covered_skills(quiz: models.Quiz) -> list[str]:
    """Catalogue skills the quiz's questions were about, in first-seen order."""
    seen = dict.fromkeys(s for q in quiz.questions for s in q.skill_ids)
    return [s for s in seen if catalogue.get_skill(s) is not None]


def _where(ref: dict | None, kind: str) -> str:
    if not ref:
        return "the project"
    if kind == "design":
        return f"the section '{ref.get('section')}'" if ref.get("section") else "the case study"
    lines = f" lines {ref['start_line']}-{ref['end_line']}" if ref.get("start_line") else ""
    return f"{ref['path']}{lines}"


def gap_flag(quiz: models.Quiz) -> FlagInput:
    """The understanding_gap text (QUIZ.md section 5), written from the weakest questions. Never says
    the student didn't build anything: it names what to review."""
    weak = sorted(
        (q for q in quiz.questions if q.answer is not None and (q.answer.score or 0.0) < WEAK_Q),
        key=lambda q: ((q.answer.score or 0.0), q.order),
    )[:GAP_QUESTIONS]
    if not weak:
        return FlagInput(
            code="understanding_gap",
            severity="medium",
            reason="Understanding of this project was not demonstrated yet in the latest verify check.",
            fix="Review the files in your quiz results, then retake the check after the cool-down.",
        )
    first = weak[0]
    path = (first.source_ref or {}).get("path") or "the project"
    where = "" if quiz.kind == "design" else f" in {path}"
    reason = f'Your answers didn\'t yet cover "{topic_text(first)}"{where}.'
    places = [_where(q.source_ref, quiz.kind) for q in weak]
    review = " and ".join(dict.fromkeys(places))
    fix = f"Review {review}; explain the flow to a friend; retake the check after the cool-down."
    return FlagInput(code="understanding_gap", severity="medium", reason=reason, fix=fix)


def _with_text(new: list[ProjectAudit], old: list[ProjectAudit]) -> list[ProjectAudit]:
    """The model-written project text (summary, rewrite, issues) is not recomputed; carry it over."""
    before = {p.project_id: p for p in old}
    out = []
    for audit in new:
        prior = before.get(audit.project_id)
        if prior is not None:
            audit = audit.model_copy(
                update={
                    "what_it_does": prior.what_it_does,
                    "honest_rewrite": prior.honest_rewrite,
                    "issues": prior.issues,
                }
            )
        out.append(audit)
    return out


def _keep_ticks(new: list[RoadmapMilestone], old: list[RoadmapMilestone]) -> list[RoadmapMilestone]:
    """A re-planned milestone that addresses the same things as a ticked one stays ticked."""
    ticked = {frozenset(m.addresses) for m in old if m.done}
    titles = {m.title for m in old if m.done}
    return [
        m.model_copy(update={"done": True}) if frozenset(m.addresses) in ticked or m.title in titles else m
        for m in new
    ]


def apply_verify_result(
    db: Session, quiz: models.Quiz, deps: PipelineDeps
) -> tuple[SimulationResult, ProjectFlag | None] | None:
    """Re-score the quiz's analysis with this result. None if the analysis can't be re-scored."""
    analysis = quiz.analysis
    if not analysis.signals or not analysis.report or not quiz.understanding:
        return None
    inputs = ScoringInputs.model_validate(analysis.signals)
    project = next((p for p in inputs.projects if p.project_id == quiz.project_id), None)
    if project is None:
        return None
    understanding = Understanding(quiz.understanding)
    updated: ProjectInput = project.model_copy(
        update={
            "understanding": understanding,
            "covered_skill_ids": covered_skills(quiz),
            "latest_quiz_id": UUID(quiz.id),
            "gap_flag": gap_flag(quiz) if understanding == Understanding.not_demonstrated else None,
        }
    )
    new_inputs = inputs.model_copy(
        update={"projects": [updated if p.project_id == project.project_id else p for p in inputs.projects]}
    )

    old = AnalysisReport.model_validate(analysis.report)
    result = scoring.score(new_inputs)
    role = catalogue.get_role(new_inputs.target_role_id)
    roadmap, plan_notes = plan_roadmap(new_inputs, result, role, db, providers=deps.providers)
    report = AnalysisReport(
        score=result.breakdown,
        coverage=result.coverage,
        claims=result.claims,
        gaps=result.gaps,
        projects=_with_text(result.projects, old.projects),
        role_fits=scoring.role_fits(new_inputs),
        roadmap=_keep_ticks(roadmap, old.roadmap),
        consistency=result.consistency,
        evidence=result.evidence,
        notes=[*old.notes, *(n for n in plan_notes if n not in old.notes)],
    )
    store_report(analysis, new_inputs, report)
    profile = analysis.profile
    if profile.latest_analysis_id == analysis.id:
        profile.latest_score = report.score.total
    if project.url:  # carried into every later analysis of this profile (QUIZ.md section 5)
        stored = dict(profile.project_understanding or {})
        stored[project.url] = {
            "understanding": understanding.value,
            "covered_skill_ids": updated.covered_skill_ids,
            "quiz_id": quiz.id,
        }
        profile.project_understanding = stored

    update = SimulationResult(
        before=old.score, after=report.score, delta=round(report.score.total - old.score.total, 1)
    )
    audit = next((p for p in report.projects if p.project_id == project.project_id), None)
    flag = next((f for f in (audit.flags if audit else []) if f.code == "understanding_gap"), None)
    return update, flag
