"""Stage 7 (docs/PIPELINE.md): the improvement roadmap.

The LLM only chooses which gaps and flags to tackle, writes each deliverable and picks resource ids.
Python then drops unknown ids, strips any URL the model wrote, attaches the real resources from
`data/resources.yaml`, computes every `estimated_gain` with the scoring engine, orders by gain per
hour and numbers the milestones. If the model fails or says nothing usable, a deterministic
roadmap is built from the same gaps and flags, so planning never fails an analysis.
"""

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app import catalogue
from app.catalogue import RoleDef
from app.prompts import load_prompt
from app.schemas.api import (
    EvidenceLevel,
    RoadmapMilestone,
    SimulationChange,
    SkillLevelChange,
    Understanding,
)
from app.schemas.llm import RoadmapPlan
from app.services.llm import LLMError, Provider, generate_structured
from app.services.scoring import changes_gain
from app.services.scoring_inputs import ScoreResult, ScoringInputs

logger = logging.getLogger("careerlens.planner")

MIN_MILESTONES = 4
MAX_MILESTONES = 7
MAX_GAPS = 8
MAX_FLAGS = 8
MAX_RESOURCES_PER_MILESTONE = 3
MAX_EFFORT_HOURS = 80
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


@dataclass
class Candidate:
    """Something a milestone can address: a skill gap or a project flag."""

    id: str
    change: SimulationChange
    skill_id: str | None = None  # gaps
    project: str = ""  # flags
    code: str = ""  # flags
    fix: str = ""
    gain: float = 0.0
    importance: int = 1


@dataclass
class Draft:
    title: str
    deliverable: str
    addresses: list[str]
    resource_ids: list[str]
    effort_hours: int
    order: int = 0
    gain: float = field(default=0.0)


def _candidates(result: ScoreResult) -> dict[str, Candidate]:
    found: dict[str, Candidate] = {}
    for gap in result.gaps[:MAX_GAPS]:
        found[gap.gap_id] = Candidate(
            id=gap.gap_id,
            change=SimulationChange(
                set_skill_level=SkillLevelChange(skill_id=gap.skill_id, level=EvidenceLevel.strong)
            ),
            skill_id=gap.skill_id,
            gain=gap.estimated_gain,
            importance=gap.importance,
        )
    flags = [(p, f) for p in result.projects for f in p.flags]
    flags.sort(key=lambda pf: (-pf[1].estimated_gain, pf[1].flag_id))
    for project, flag in flags[:MAX_FLAGS]:
        change = (
            SimulationChange(project_id=project.project_id, set_understanding=Understanding.demonstrated)
            if flag.code == "understanding_gap"
            else SimulationChange(resolve_flags=[flag.flag_id])
        )
        found[flag.flag_id] = Candidate(
            id=flag.flag_id,
            change=change,
            project=project.title,
            code=flag.code,
            fix=flag.fix,
            gain=flag.estimated_gain,
        )
    return found


def _resources_for(candidates: dict[str, Candidate]) -> dict[str, "catalogue.Resource"]:
    skills = {c.skill_id for c in candidates.values() if c.skill_id}
    return {r.id: r for s in sorted(skills) for r in catalogue.resources_for(s)}


# ---------------------------------------------------------------- the LLM step


def _prompt_lists(result: ScoreResult, candidates: dict[str, Candidate], resources: dict) -> dict[str, str]:
    gaps = [
        f"{g.gap_id} | {g.skill_name} | {g.level.value} | +{g.estimated_gain:g}"
        for g in result.gaps[:MAX_GAPS]
    ]
    flags = [
        f"{c.id} | {c.project} | {c.code} | {c.fix} | +{c.gain:g}" for c in candidates.values() if c.code
    ]
    catalogue_lines = [
        f"{r.id} | {r.skill_id} | {r.title} | {r.type} | {r.hours or '?'}h" for r in resources.values()
    ]
    breakdown = ", ".join(
        f"{c.label} {c.score if c.score is not None else 'no data'}" for c in result.breakdown.components
    )
    return {
        "gaps": "\n".join(gaps) or "(none)",
        "flags": "\n".join(flags) or "(none)",
        "catalogue": "\n".join(catalogue_lines) or "(none)",
        "breakdown": breakdown,
    }


def _clean_text(text: str) -> str:
    return " ".join(_URL.sub("", text).split())


def _validated(plan: RoadmapPlan, candidates: dict[str, Candidate], resources: dict) -> list[Draft]:
    drafts = []
    for index, m in enumerate(plan.milestones):
        addresses = [a for a in dict.fromkeys(m.addresses) if a in candidates]
        title, deliverable = _clean_text(m.title), _clean_text(m.deliverable)
        if not addresses or not title or not deliverable:
            continue  # a milestone must name something real to improve and a concrete deliverable
        resource_ids = [r for r in dict.fromkeys(m.resource_ids) if r in resources][
            :MAX_RESOURCES_PER_MILESTONE
        ]
        drafts.append(
            Draft(
                title,
                deliverable,
                addresses,
                resource_ids,
                min(max(m.effort_hours, 1), MAX_EFFORT_HOURS),
                index,
            )
        )
    return drafts


# ---------------------------------------------------------------- deterministic fallback

# code -> (title, deliverable, effort hours); {p} is the project name
_FLAG_PLANS = {
    "single_dump": ("Show how {p} was built step by step", "A commit history and CHANGELOG for {p}", 2),
    "unmodified_fork": ("Add your own work to {p}", "A feature or fix of your own in {p}", 6),
    "default_readme": ("Write a real README for {p}", "A README with the problem, setup and screenshots", 2),
    "tutorial_pattern": ("Extend {p} beyond the tutorial", "One original feature with tests and a demo", 8),
    "thin_wrapper": ("Describe or deepen {p}", "An accurate description, or measured results for it", 6),
    "claim_mismatch": (
        "Link the code behind a claim in {p}",
        "Remove the claim, or add and link the code",
        2,
    ),
    "vague_description": (
        "Make the {p} description specific",
        "One number and one sentence on how it works",
        1,
    ),
    "understanding_gap": (
        "Review {p} and retake the check",
        "Explain the key files in {p} aloud, then retake the verify check after the cool-down",
        3,
    ),
}


def _fallback_draft(c: Candidate, result: ScoreResult, resources: dict) -> Draft:
    if c.skill_id:
        name = next((g.skill_name for g in result.gaps if g.gap_id == c.id), c.skill_id)
        ids = [r.id for r in resources.values() if r.skill_id == c.skill_id][:2]
        return Draft(
            f"Show {name} in a project",
            f"A public repository or case study where {name} is used and the work is visible",
            [c.id],
            ids,
            6 if c.importance >= 2 else 4,
        )
    title, deliverable, hours = _FLAG_PLANS[c.code]
    return Draft(title.format(p=c.project), deliverable.format(p=c.project), [c.id], [], hours)


# ---------------------------------------------------------------- public entry point


def plan_roadmap(
    inputs: ScoringInputs,
    result: ScoreResult,
    role: RoleDef,
    db: Session,
    *,
    providers: list[Provider] | None = None,
    refresh: bool = False,
) -> tuple[list[RoadmapMilestone], list[str]]:
    """The roadmap and any notes about how it was made."""
    candidates = _candidates(result)
    if not candidates:
        return [], []
    resources = _resources_for(candidates)
    notes: list[str] = []

    drafts: list[Draft] = []
    try:
        prompt = load_prompt("plan_roadmap")
        user = prompt.user(
            role_name=role.name,
            score=f"{result.breakdown.total:g}",
            band=result.breakdown.band.value,
            **_prompt_lists(result, candidates, resources),
        )
        plan = generate_structured(
            RoadmapPlan, prompt.system, user, tier="fast", db=db, force_refresh=refresh, providers=providers
        )
        drafts = _validated(plan, candidates, resources)
    except LLMError as exc:
        if exc.code == "llm_key_rejected":
            raise
        logger.warning("roadmap planner unavailable: %s", exc.code)
        notes.append(
            "The roadmap was built from the gaps and flags directly because the AI planner was unavailable."
        )

    def by_value(d: Draft) -> tuple:
        return (-d.gain / d.effort_hours, d.order, d.addresses)

    def fallback(c: Candidate, order: int) -> Draft:
        d = _fallback_draft(c, result, resources)
        d.gain, d.order = changes_gain(inputs, [c.change], role.id), order
        return d

    for d in drafts:
        d.gain = changes_gain(inputs, [candidates[a].change for a in d.addresses], role.id)

    # An understanding_gap always gets its own milestone (QUIZ.md section 7), even if the model skipped it.
    must = {c.id for c in candidates.values() if c.code == "understanding_gap"}
    covered = {a for d in drafts for a in d.addresses}
    drafts += [fallback(candidates[i], 1000 + n) for n, i in enumerate(sorted(must - covered))]
    drafts.sort(key=by_value)
    required = [d for d in drafts if must & set(d.addresses)]
    drafts = sorted((required + [d for d in drafts if d not in required])[:MAX_MILESTONES], key=by_value)

    if len(drafts) < MIN_MILESTONES:  # top up from what is not covered yet, best gain first
        covered = {a for d in drafts for a in d.addresses}
        spare = sorted((c for c in candidates.values() if c.id not in covered), key=lambda c: (-c.gain, c.id))
        extra = [fallback(c, 2000 + n) for n, c in enumerate(spare[: MIN_MILESTONES - len(drafts)])]
        drafts += sorted(extra, key=by_value)

    milestones = []
    for n, d in enumerate(drafts, start=1):
        milestones.append(
            RoadmapMilestone(
                id=f"ms-{n}",
                order=n,
                title=d.title,
                deliverable=d.deliverable,
                addresses=d.addresses,
                resources=[resources[r] for r in d.resource_ids] if d.resource_ids else [],
                effort_hours=d.effort_hours,
                estimated_gain=round(d.gain, 1),
            )
        )
    return milestones, notes
