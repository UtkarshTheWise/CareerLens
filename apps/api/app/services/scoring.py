"""Job Readiness Score engine (docs/SCORING.md). Pure: same input, same output.

No I/O, no LLM, no network, no clock (`ScoringInputs.today` is passed in). B6 builds the inputs and
stores them with the analysis, so re-scoring after a quiz and every what-if is `score(stored_inputs)`.

Convention for `ScoreComponent.reasons[]`: each `delta` is the points, on the component's 0-100 scale,
that an item earned (+); an item that earned nothing gets a negative entry for the points it could
have added. So within a component the positive deltas sum to the component score.
"""

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field

from app import catalogue
from app.catalogue import RoleDef
from app.schemas.api import (
    Band,
    Confidence,
    ConsistencySummary,
    DesignSubscores,
    Evidence,
    EvidenceLevel,
    ProjectAudit,
    ProjectFlag,
    ProjectSubscores,
    RoleFit,
    ScoreBreakdown,
    ScoreComponent,
    ScoreReason,
    SimulationChange,
    SimulationRequest,
    SimulationResult,
    SkillClaim,
    SkillGap,
    Understanding,
    WeekCount,
)
from app.services.detectors import DetectorHit, depth_parts, to_project_signals
from app.services.scoring_inputs import (
    FlagInput,
    ProjectInput,
    ScoreResult,
    ScoringInputs,
    SimulationError,
)

# ---------------------------------------------------------------- constants (docs/SCORING.md)

CREDIT = {"strong": 1.0, "moderate": 0.70, "weak": 0.35, "unverified": 0.10, "missing": 0.0}
LEVELS = ["missing", "unverified", "weak", "moderate", "strong"]  # ascending
RANK = {level: i for i, level in enumerate(LEVELS)}
STEP_DOWN = {"strong": "moderate", "moderate": "weak", "weak": "unverified", "unverified": "unverified"}
VERIFIED = {"strong", "moderate"}

STRONG_MIN_COMMITS = 5
STRONG_MIN_SHARE = 0.40
QUIZ_BONUS = 5
DESIGN_CAP = 80
LOW_CONFIDENCE_CAP = 60.0
CALENDAR_WEEKS = 26
TOP_PROJECTS = 3
MAX_SKILLS_LISTED = 25

COMPONENTS = ["skill_evidence", "project_quality", "consistency", "experience", "resume_quality"]
LABELS = {
    "skill_evidence": "Skill evidence",
    "project_quality": "Project quality",
    "consistency": "Consistency",
    "experience": "Experience",
    "resume_quality": "Resume quality",
}

_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_METRIC = re.compile(r"\d+(?:\.\d+)?%|\d+(?:\.\d+)?x\b|\d{2,}")


# ---------------------------------------------------------------- small helpers


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def project_id_for(title: str) -> str:
    return f"proj-{slug(title)}"


def flag_id_for(project_id: str, code: str) -> str:
    return f"flag-{project_id.removeprefix('proj-')}-{code.replace('_', '-')}"


def is_quantified(text: str) -> bool:
    """A number that states a result: a percentage, a multiple, or 2+ digits, ignoring years."""
    return bool(_METRIC.search(_YEAR.sub("", text)))


def _r2(x: float) -> float:
    return round(x + 0.0, 2)


def _skill_name(skill_id: str) -> str:
    skill = catalogue.get_skill(skill_id)
    return skill.name if skill else skill_id


def _band(total: float) -> Band:
    return Band.not_ready if total < 50 else Band.developing if total < 75 else Band.ready


def _role(role_id: str) -> RoleDef:
    role = catalogue.get_role(role_id)
    if role is None:
        raise ValueError(f"unknown role '{role_id}'")
    return role


# ---------------------------------------------------------------- evidence registry and items


class _Registry:
    def __init__(self) -> None:
        self.items: dict[str, Evidence] = {}

    def add(self, evidence: Evidence) -> str:
        self.items.setdefault(evidence.id, evidence)
        return evidence.id


@dataclass
class Item:
    """One piece of evidence for one skill."""

    level: str
    reason: str
    evidence_ids: list[str]
    project_id: str | None = None
    artifact: bool = True  # False: a claim with no artifact behind it (skills list, a mention)


@dataclass
class Resolved:
    level: str
    reason: str
    evidence_ids: list[str]
    claimed: bool


def _describe(hit: DetectorHit) -> str:
    return {
        "npm": f"dependency {hit.detail}",
        "pip": f"dependency {hit.detail}",
        "maven": f"dependency {hit.detail}",
        "gradle": f"build setting {hit.detail}",
        "file": f"file {hit.detail}",
        "path": f"{hit.detail} directory",
        "extension": f"{hit.detail} source files",
        "content": f"configuration in {hit.detail}",
        "import": f"imported in {hit.detail}",
    }[hit.kind]


def _known(skill_ids) -> list[str]:
    return [s for s in dict.fromkeys(skill_ids) if catalogue.get_skill(s) is not None]


def _collect(
    inputs: ScoringInputs, reg: _Registry, notes: list[str]
) -> tuple[dict[str, list[Item]], set[str]]:
    items: dict[str, list[Item]] = defaultdict(list)
    claimed: set[str] = set()
    resume = inputs.resume

    unknown: list[str] = []
    for raw in resume.skills:
        sid = catalogue.normalize_skill(raw)
        if sid is None:
            unknown.append(raw)
            continue
        claimed.add(sid)
        ev = reg.add(
            Evidence(
                id="ev-resume-skills",
                kind="resume_text",
                source="resume",
                label="Skills section of the resume",
            )
        )
        items[sid].append(Item("unverified", "Appears only in the skills list", [ev], None, False))
    if unknown:
        names = list(dict.fromkeys(unknown))
        shown = ", ".join(names[:8]) + (f" and {len(names) - 8} more" if len(names) > 8 else "")
        notes.append(f"{len(names)} listed skill(s) are not in the catalogue and were not scored: {shown}.")

    for project in resume.projects:
        found = set(_known(catalogue.normalize_skill(t) for t in project.mentioned_technologies if t))
        found |= catalogue.find_skills_in_text(project.description)
        ev = reg.add(
            Evidence(
                id=f"ev-resume-project-{slug(project.title)}",
                kind="resume_text",
                source="resume",
                label=f"Project '{project.title}' on the resume",
            )
        )
        for sid in sorted(found):
            claimed.add(sid)
            items[sid].append(
                Item(
                    "weak",
                    f"Mentioned in the description of '{project.title}', with no linked artifact",
                    [ev],
                    None,
                    False,
                )
            )

    for n, exp in enumerate(resume.experience, start=1):
        ev = reg.add(
            Evidence(id=f"ev-exp-{n}", kind="experience", source="resume", label=f"{exp.role} at {exp.org}")
        )
        for sid in _known(catalogue.normalize_skill(t) for t in exp.mentioned_technologies if t):
            claimed.add(sid)
            items[sid].append(Item("weak", f"Named in the experience at {exp.org}", [ev], None, False))
        for bullet in exp.bullets:
            for sid in sorted(catalogue.find_skills_in_text(bullet)):
                claimed.add(sid)
                if is_quantified(bullet):
                    items[sid].append(
                        Item(
                            "moderate",
                            f"Named in a bullet with a measurable result at {exp.org}",
                            [ev],
                            None,
                            True,
                        )
                    )
                else:
                    items[sid].append(
                        Item("weak", f"Named in the experience at {exp.org}", [ev], None, False)
                    )

    if inputs.linkedin_skill_ids:
        ev = reg.add(
            Evidence(id="ev-linkedin", kind="linkedin", source="linkedin", label="LinkedIn profile text")
        )
        for sid in _known(inputs.linkedin_skill_ids):
            claimed.add(sid)
            items[sid].append(
                Item("weak", "Named in the LinkedIn profile, with no linked artifact", [ev], None, False)
            )

    for cert in resume.certifications:
        found = catalogue.find_skills_in_text(cert.name)
        if not found:
            continue
        ev = reg.add(
            Evidence(id=f"ev-cert-{slug(cert.name)}", kind="certificate", source="resume", label=cert.name)
        )
        for sid in sorted(found):
            claimed.add(sid)
            items[sid].append(Item("weak", f"Named in the certificate '{cert.name}'", [ev], None, False))

    for project in inputs.projects:
        _collect_project(project, reg, items, claimed)
    return items, claimed


def _project_evidence_id(project: ProjectInput) -> str:
    if project.kind == "design":
        return f"ev-portfolio-{slug(project.title)}"
    return f"ev-repo-{slug(project.title)}"


def _collect_project(
    project: ProjectInput, reg: _Registry, items: dict[str, list[Item]], claimed: set[str]
) -> None:
    pid = project.project_id
    if project.kind == "design":
        ev = reg.add(
            Evidence(
                id=_project_evidence_id(project),
                kind="portfolio_item",
                source="portfolio",
                label=project.title,
                url=project.url,
            )
        )
        design = project.design
        seen: set[str] = set()
        if (
            design is not None
            and design.readable
            and (design.problem_statement > 0 or design.process_evidence > 0)
        ):
            seen = {
                sid
                for sid in _known(catalogue.normalize_skill(t) for t in design.tools_seen if t)
                if catalogue.get_skill(sid).category == "design"
            }
            for sid in sorted(seen):
                items[sid].append(
                    Item(
                        "moderate",
                        f"Seen in the case study '{project.title}' (self-reported)",
                        [ev],
                        pid,
                        True,
                    )
                )
        for sid in _known(project.claimed_skill_ids):
            claimed.add(sid)
            if sid not in seen:
                items[sid].append(
                    Item(
                        "weak",
                        f"Named for '{project.title}', but not seen in its case study",
                        [ev],
                        pid,
                        False,
                    )
                )
        return

    signals = project.signals
    if signals is None:
        return
    ev = reg.add(
        Evidence(
            id=_project_evidence_id(project),
            kind="repo",
            source="github",
            label=f"{project.title} ({signals.authored_commits} of {signals.total_commits} commits authored)",
            url=project.url,
            details={
                "authored_commits": signals.authored_commits,
                "total_commits": signals.total_commits,
                "is_fork": signals.is_fork,
            },
        )
    )
    for sid in _known(project.claimed_skill_ids):
        claimed.add(sid)
        items[sid].append(Item("weak", f"Named in the description of '{project.title}'", [ev], pid, False))
    if signals.is_fork and signals.fork_authored_commits == 0:
        return  # an untouched fork shows nothing of the student's own
    strong_ok = (
        not signals.is_fork
        and signals.authored_commits >= STRONG_MIN_COMMITS
        and signals.authored_share >= STRONG_MIN_SHARE
    )
    own = f"{signals.authored_commits} of {signals.total_commits} commits are yours"
    for sid in _known(project.skills):
        hits = project.skills[sid]
        ids = [ev]
        for hit in hits:
            if hit.kind in ("file", "content", "import") and len(ids) < 3 and project.url:
                ids.append(
                    reg.add(
                        Evidence(
                            id=f"ev-file-{slug(project.title)}-{slug(hit.detail)}",
                            kind="file",
                            source="github",
                            label=hit.detail,
                            url=f"{project.url}/blob/HEAD/{hit.detail}",
                        )
                    )
                )
        items[sid].append(
            Item(
                "strong" if strong_ok else "moderate",
                f"{_skill_name(sid)} found in '{project.title}' ({_describe(hits[0])}; {own})",
                ids,
                pid,
                True,
            )
        )
    for sid in _known(project.language_skills):
        items[sid].append(
            Item("moderate", f"{_skill_name(sid)} is the main language of '{project.title}'", [ev], pid, True)
        )


def _apply_quiz(items: dict[str, list[Item]], projects: list[ProjectInput]) -> None:
    """SCORING §6: applied to the evidence levels, before the components."""
    for project in projects:
        covered = [s for s in dict.fromkeys(project.covered_skill_ids) if s in items]
        if project.understanding == Understanding.demonstrated:
            for sid in covered:
                for item in items[sid]:
                    if item.project_id != project.project_id:
                        continue
                    if project.kind == "code" and item.artifact and item.level == "moderate":
                        item.level = "strong"
                        item.reason += "; understanding verified in a quiz"
                    elif project.kind == "design" and item.level == "weak":
                        item.level = "moderate"  # never above moderate for self-reported design work
                        item.reason += "; understanding verified in a quiz"
        elif project.understanding == Understanding.not_demonstrated:
            for sid in covered:
                artifacts = [i for i in items[sid] if i.artifact]
                if artifacts and all(i.project_id == project.project_id for i in artifacts):
                    for item in artifacts:
                        item.level = STEP_DOWN[item.level]
                        item.reason += "; understanding not demonstrated yet in a quiz"


def _resolve(
    items: dict[str, list[Item]], claimed: set[str], role: RoleDef, overrides: dict[str, str]
) -> dict[str, Resolved]:
    resolved: dict[str, Resolved] = {}
    wanted = set(items) | claimed | {rs.skill_id for rs in role.skills} | set(overrides)
    for sid in sorted(wanted):
        if sid in overrides:
            level = overrides[sid]
            resolved[sid] = Resolved(level, f"Set to {level} for a what-if", [], sid in claimed)
            continue
        candidates = items.get(sid, [])
        if not candidates:
            resolved[sid] = Resolved(
                "missing",
                f"Required for {role.name}; not claimed and not found in any repository",
                [],
                False,
            )
            continue
        best = max(candidates, key=lambda i: (RANK[i.level], i.artifact))
        resolved[sid] = Resolved(best.level, best.reason, best.evidence_ids, sid in claimed)
    return resolved


# ---------------------------------------------------------------- component A: skill evidence


def _reason(text: str, delta: float, evidence_ids: list[str] | None = None) -> ScoreReason:
    return ScoreReason(text=text, delta=_r2(delta), evidence_ids=list(evidence_ids or []))


def _component_a(role: RoleDef, levels: dict[str, Resolved]) -> tuple[float, list[ScoreReason]]:
    total_weight = sum(rs.importance for rs in role.skills)
    ordered = sorted(
        role.skills, key=lambda rs: (-rs.importance, -CREDIT[levels[rs.skill_id].level], rs.skill_name)
    )
    score = 0.0
    reasons: list[ScoreReason] = []
    for rs in ordered:
        res = levels[rs.skill_id]
        full = 100 * rs.importance / total_weight
        earned = full * CREDIT[res.level]
        score += earned
        if earned > 0:
            more = (
                f"; stronger evidence would add up to {full - earned:.1f} more points"
                if res.level != "strong"
                else ""
            )
            reasons.append(
                _reason(f"{rs.skill_name} ({res.level}): {res.reason}{more}", earned, res.evidence_ids)
            )
        else:
            reasons.append(
                _reason(
                    f"{rs.skill_name} is required for {role.name} and has no evidence yet",
                    -full,
                    res.evidence_ids,
                )
            )
    return score, reasons


# ---------------------------------------------------------------- component B: project quality


@dataclass
class ScoredProject:
    project: ProjectInput
    flags: list[FlagInput]
    score: float
    subscores: ProjectSubscores | None
    design_subscores: DesignSubscores | None
    missing: list[tuple[str, float]] = field(default_factory=list)  # (what is missing, points)
    relevance: int = 0
    counted: bool = False


def _flags_for(project: ProjectInput) -> list[FlagInput]:
    flags = {f.code: f for f in project.flags if f.code != "understanding_gap"}
    if project.understanding == Understanding.not_demonstrated:
        flags["understanding_gap"] = project.gap_flag or FlagInput(
            code="understanding_gap",
            severity="medium",
            reason="Understanding of this project was not demonstrated yet in the latest verify check.",
            fix="Review the files and lines in your quiz results, then retake the check after the cool-down.",
        )
    return list(flags.values())


def _score_code(project: ProjectInput, flags: list[FlagInput]) -> ScoredProject:
    s = project.signals
    assert s is not None
    missing: list[tuple[str, float]] = []

    def award(ok: bool, points: float, label: str) -> float:
        if not ok:
            missing.append((label, points))
        return points if ok else 0.0

    hygiene = (
        award(s.readme_substantive, 8, "a README with real content")
        + award(s.has_description, 3, "a repository description")
        + award(s.has_license, 3, "a licence")
        + award(s.has_demo_url, 4, "a demo link")
        + award(s.readme_has_setup_or_screenshots, 2, "setup steps or screenshots in the README")
    )
    engineering = (
        award(s.has_tests, 10, "tests")
        + award(s.has_ci, 8, "CI")
        + award(s.has_manifest and s.has_lockfile, 4, "a dependency manifest with a lockfile")
        + award(s.module_count >= 2, 4, "a structured source tree")
        + award(s.has_deploy_config, 4, "a deploy configuration")
    )
    share = max(0.0, min(1.0, (s.authored_share - 0.20) / 0.40)) * 15
    if share < 15:
        missing.append(("a larger share of the commits", 15 - share))
    original = award(not s.is_fork or s.fork_authored_commits >= 5, 5, "own work beyond the original fork")
    flag_points = max(0, 10 - 5 * len(flags))
    if flag_points < 10:
        missing.append((f"{len(flags)} low-evidence flag(s) to resolve", 10 - flag_points))
    authorship = share + original + flag_points
    if project.understanding == Understanding.demonstrated:
        authorship += QUIZ_BONUS
    authorship = min(authorship, 30.0)
    commits, span, code = depth_parts(s)
    depth = commits + span + code
    for label, got, full in (
        ("more authored commits", commits, 8),
        ("a longer active span", span, 6),
        ("more code", code, 6),
    ):
        if got < full:
            missing.append((label, full - got))
    total = hygiene + engineering + authorship + depth
    return ScoredProject(
        project,
        flags,
        total,
        ProjectSubscores(
            hygiene=_r2(hygiene), engineering=_r2(engineering), authorship=_r2(authorship), depth=_r2(depth)
        ),
        None,
        missing,
    )


def _score_design(project: ProjectInput, flags: list[FlagInput]) -> ScoredProject:
    d = project.design
    if d is None or not d.readable:
        return ScoredProject(
            project, flags, 0.0, None, DesignSubscores(), [("a readable case study", DESIGN_CAP)]
        )
    total = float(min(d.total, DESIGN_CAP))
    if project.understanding == Understanding.demonstrated:
        total = min(total + QUIZ_BONUS, float(DESIGN_CAP))
    elif project.understanding == Understanding.not_demonstrated:
        total = max(total - QUIZ_BONUS, 0.0)
    missing = [
        (label, full - got)
        for label, got, full in (
            ("a clear problem statement", d.problem_statement, 25),
            ("process evidence", d.process_evidence, 30),
            ("outcomes or metrics", d.outcome_or_metrics, 20),
            ("tools shown", d.tool_evidence, 15),
            ("presentation", d.presentation, 10),
        )
        if got < full
    ]
    return ScoredProject(
        project,
        flags,
        total,
        None,
        DesignSubscores(
            problem_statement=d.problem_statement,
            process_evidence=d.process_evidence,
            outcome_or_metrics=d.outcome_or_metrics,
            tool_evidence=d.tool_evidence,
            presentation=d.presentation,
        ),
        missing,
    )


def _evidenced_skills(project: ProjectInput) -> set[str]:
    skills = set(_known(project.skills)) | set(_known(project.language_skills))
    if project.kind == "design" and project.design is not None and project.design.readable:
        skills |= {
            sid
            for sid in _known(catalogue.normalize_skill(t) for t in project.design.tools_seen if t)
            if catalogue.get_skill(sid).category == "design"
        }
    return skills


def _score_projects(inputs: ScoringInputs, role: RoleDef) -> list[ScoredProject]:
    importance = {rs.skill_id: rs.importance for rs in role.skills}
    scored: list[ScoredProject] = []
    for project in inputs.projects:
        flags = _flags_for(project)
        if project.kind == "design":
            sp = _score_design(project, flags)
        elif project.signals is not None:
            sp = _score_code(project, flags)
        else:
            continue
        sp.relevance = sum(importance.get(sid, 0) for sid in _evidenced_skills(project))
        scored.append(sp)
    candidates = [sp for sp in scored if sp.project.kind == "design"] if role.is_design else scored
    for sp in sorted(candidates, key=lambda sp: (-sp.relevance, -sp.score, sp.project.project_id))[
        :TOP_PROJECTS
    ]:
        sp.counted = True
    return scored


def _component_b(
    scored: list[ScoredProject], role: RoleDef, reg: _Registry
) -> tuple[float | None, list[ScoreReason]]:
    counted = [sp for sp in scored if sp.counted]
    if not counted:
        if role.is_design:
            return 0.0, [
                _reason("No portfolio items are linked, and design roles are scored on portfolio work", -100)
            ]
        return None, [
            _reason("No repositories or portfolio items were found, so project quality can't be measured", 0)
        ]
    n = len(counted)
    reasons: list[ScoreReason] = []
    for sp in counted:
        ev = [_project_evidence_id(sp.project)] if _project_evidence_id(sp.project) in reg.items else []
        title = sp.project.title
        if sp.score > 0:
            note = " (self-reported evidence, capped at 80)" if sp.project.kind == "design" else ""
            reasons.append(_reason(f"'{title}' scored {sp.score:.0f}/100{note}", sp.score / n, ev))
        if sp.score < 100:
            top = sorted(sp.missing, key=lambda m: -m[1])[:3]
            what = ", ".join(f"{label} ({points:.0f})" for label, points in top) or "more evidence"
            reasons.append(_reason(f"Points not earned by '{title}': {what}", -(100 - sp.score) / n, ev))
    return sum(sp.score for sp in counted) / n, reasons


# ---------------------------------------------------------------- component C: consistency


def _component_c(inputs: ScoringInputs) -> tuple[float | None, list[ScoreReason], ConsistencySummary | None]:
    if not inputs.github_linked:
        return None, [_reason("No GitHub account is linked, so consistency can't be measured", 0)], None
    counts = [w.count for w in inputs.weeks][-CALENDAR_WEEKS:]
    counts = [0] * (CALENDAR_WEEKS - len(counts)) + counts
    active = sum(1 for c in counts if c > 0)
    mean = sum(counts) / CALENDAR_WEEKS
    cv = math.sqrt(sum((c - mean) ** 2 for c in counts) / CALENDAR_WEEKS) / mean if mean > 0 else None
    stability = 0.0 if cv is None else 1 - min(cv, 2.0) / 2
    if inputs.last_active_date is None:
        days, recency = None, 0.0
    else:
        days = max(0, (inputs.today - inputs.last_active_date).days)
        recency = 1.0 if days <= 14 else 0.0 if days >= 90 else 1 - (days - 14) / 76
    ratio_pts, stab_pts, rec_pts = 50 * active / CALENDAR_WEEKS, 30 * stability, 20 * recency
    score = ratio_pts + stab_pts + rec_pts

    def entry(text_up: str, text_zero: str, pts: float, full: float) -> ScoreReason:
        return _reason(text_up, pts) if pts > 0 else _reason(text_zero, -full)

    reasons = [
        entry(
            f"Active in {active} of the last {CALENDAR_WEEKS} weeks",
            "No active weeks in the last 26",
            ratio_pts,
            50,
        ),
        entry(
            "Weekly activity is steady" if cv is not None and cv <= 1 else "Weekly activity comes in bursts",
            "No activity to measure steadiness",
            stab_pts,
            30,
        ),
        entry(
            f"Last activity {days} days ago" if days is not None else "Recent activity",
            "No recent activity",
            rec_pts,
            20,
        ),
    ]
    summary = ConsistencySummary(
        weeks=[WeekCount(week_start=w.week_start, count=w.count) for w in inputs.weeks],
        active_weeks=active,
        cv=None if cv is None else round(cv, 3),
        last_active_date=inputs.last_active_date,
        score=round(score, 1),
    )
    return score, reasons, summary


# ---------------------------------------------------------------- components D and E: experience, resume


def _component_d(inputs: ScoringInputs, reg: _Registry) -> tuple[float, list[ScoreReason]]:
    experience = inputs.resume.experience
    bullets = [b for e in experience for b in e.bullets]
    quantified = sum(1 for b in bullets if is_quantified(b))
    ratio = quantified / len(bullets) if bullets else 0.0
    base = 0 if not experience else 60 if len(experience) == 1 else 100
    score = base * (0.6 + 0.4 * ratio)
    ev = [f"ev-exp-{n}" for n in range(1, len(experience) + 1) if f"ev-exp-{n}" in reg.items]
    reasons: list[ScoreReason] = []
    if score > 0:
        reasons.append(
            _reason(
                f"{len(experience)} role(s); {quantified} of {len(bullets)} bullets have a measurable result",
                score,
                ev,
            )
        )
    if score < 100:
        why = []
        if len(experience) < 2:
            why.append(
                "a second role, internship or freelance project"
                if experience
                else "an internship, job or project role"
            )
        if ratio < 1:
            why.append("numbers in the bullets")
        reasons.append(_reason(f"Points not earned: {' and '.join(why)}", -(100 - score)))
    return score, reasons


def _component_e(
    inputs: ScoringInputs, levels: dict[str, Resolved], notes: list[str]
) -> tuple[float, list[ScoreReason]]:
    resume = inputs.resume
    reasons: list[ScoreReason] = []
    score = 0.0

    def item(ok: bool, points: float, yes: str, no: str, ev: list[str] | None = None) -> None:
        nonlocal score
        if ok:
            score += points
            reasons.append(_reason(yes, points, ev))
        else:
            reasons.append(_reason(no, -points))

    for label, ok in (
        ("contact details", inputs.has_contact),
        ("education", bool(resume.education)),
        ("a skills section", bool(resume.skills)),
        ("projects", bool(resume.projects)),
        ("experience", bool(resume.experience)),
    ):
        item(ok, 8, f"The resume has {label}", f"The resume has no {label}")

    units = [b for e in resume.experience for b in e.bullets] + [p.description for p in resume.projects]
    quantified = sum(1 for u in units if is_quantified(u))
    ratio = quantified / len(units) if units else 0.0
    earned = 30 * ratio
    score += earned
    reasons.append(
        _reason(f"{quantified} of {len(units)} bullets and project descriptions include a number", earned)
        if earned > 0
        else _reason("No bullet or project description includes a number", -30)
    )

    pages = resume.page_count_hint
    if pages is None:
        notes.append("The resume's page count is unknown (Word or plain text), so length was not penalised.")
        item(True, 15, "Page count unknown (Word or plain-text file); length not penalised", "")
    else:
        item(
            1 <= pages <= 2,
            15,
            f"The resume is {pages} page(s)",
            f"The resume is {pages} pages; one or two is easiest to read",
        )

    claimed_levels = [levels[s].level for s in levels if levels[s].claimed]
    unverified_share = (
        sum(1 for lv in claimed_levels if lv == "unverified") / len(claimed_levels) if claimed_levels else 0.0
    )
    listed = len(resume.skills)
    item(
        0 < listed <= MAX_SKILLS_LISTED and unverified_share < 0.5,
        15,
        f"{listed} skills listed, and most have evidence behind them",
        "The skills list is long or mostly unverified; list fewer skills you can show work for"
        if listed
        else "There is no skills list",
    )
    return score, reasons


# ---------------------------------------------------------------- aggregation


def confidence_for(inputs: ScoringInputs, role: RoleDef) -> Confidence:
    """SCORING §3: from the sources besides the resume. High needs GitHub unless the role is a design role."""
    portfolio = any(
        p.kind == "design" and p.design is not None and p.design.readable for p in inputs.projects
    )
    others = int(inputs.github_linked) + int(inputs.has_linkedin) + int(portfolio)
    if others >= 2 and (inputs.github_linked or role.is_design):
        return Confidence.high
    return Confidence.medium if others >= 1 else Confidence.low


@dataclass
class Core:
    role: RoleDef
    levels: dict[str, Resolved]
    breakdown: ScoreBreakdown
    coverage: float
    scored: list[ScoredProject]
    consistency: ConsistencySummary | None
    registry: _Registry
    notes: list[str]


def _core(inputs: ScoringInputs, role: RoleDef) -> Core:
    reg, notes = _Registry(), []
    items, claimed = _collect(inputs, reg, notes)
    _apply_quiz(items, inputs.projects)
    levels = _resolve(items, claimed, role, dict(inputs.skill_overrides))
    scored = _score_projects(inputs, role)

    a_score, a_reasons = _component_a(role, levels)
    b_score, b_reasons = _component_b(scored, role, reg)
    c_score, c_reasons, consistency = _component_c(inputs)
    d_score, d_reasons = _component_d(inputs, reg)
    e_score, e_reasons = _component_e(inputs, levels, notes)
    raw = {
        "skill_evidence": (a_score, a_reasons),
        "project_quality": (b_score, b_reasons),
        "consistency": (c_score, c_reasons),
        "experience": (d_score, d_reasons),
        "resume_quality": (e_score, e_reasons),
    }

    weights = role.weights.model_dump()
    available = {k: weights[k] for k in COMPONENTS if raw[k][0] is not None}
    total_available = sum(available.values())
    dropped = [k for k in COMPONENTS if k not in available]
    if dropped:
        names = " and ".join(LABELS[k].lower() for k in dropped)
        share = sum(weights[k] for k in dropped)
        notes.append(f"No data for {names}: its {share:.0%} weight was shared across the other components.")

    components, total = [], 0.0
    for key in COMPONENTS:
        score, reasons = raw[key]
        weight = available[key] / total_available if key in available else 0.0
        contribution = weight * score if score is not None else 0.0
        total += contribution
        components.append(
            ScoreComponent(
                key=key,
                label=LABELS[key],
                weight=round(weight, 4),
                score=None if score is None else round(score, 1),
                contribution=_r2(contribution),
                reasons=reasons,
            )
        )

    confidence = confidence_for(inputs, role)
    total = round(total, 1)
    capped = False
    if confidence == Confidence.low:
        notes.append(
            "Confidence is low (resume only): the score is capped at 60 until another source is added."
        )
        if total > LOW_CONFIDENCE_CAP:
            total, capped = LOW_CONFIDENCE_CAP, True

    claimed_levels = [levels[s].level for s in levels if levels[s].claimed]
    if claimed_levels:
        coverage = round(100 * sum(1 for lv in claimed_levels if lv in VERIFIED) / len(claimed_levels), 1)
    else:
        coverage = 0.0
        notes.append("No catalogue skills were found on the resume, so Evidence Coverage is 0.")

    breakdown = ScoreBreakdown(
        total=total, band=_band(total), confidence=confidence, capped=capped, components=components
    )
    return Core(role, levels, breakdown, coverage, scored, consistency, reg, notes)


def _total(inputs: ScoringInputs, role: RoleDef) -> float:
    return _core(inputs, role).breakdown.total


# ---------------------------------------------------------------- public API


def score(inputs: ScoringInputs, role_id: str | None = None) -> ScoreResult:
    role = _role(role_id or inputs.target_role_id)
    core = _core(inputs, role)
    base = core.breakdown.total

    required = {rs.skill_id: rs for rs in role.skills}
    claims = [
        SkillClaim(
            skill_id=sid,
            skill_name=_skill_name(sid),
            claimed=res.claimed,
            level=EvidenceLevel(res.level),
            reason=res.reason,
            evidence_ids=res.evidence_ids,
        )
        for sid, res in core.levels.items()
        if res.claimed or sid in required
    ]
    claims.sort(key=lambda c: (-RANK[c.level.value], c.skill_name))

    gaps = []
    for sid, rs in required.items():
        res = core.levels[sid]
        if res.level in VERIFIED:
            continue
        lifted = inputs.model_copy(update={"skill_overrides": {**inputs.skill_overrides, sid: "strong"}})
        gaps.append(
            SkillGap(
                gap_id=f"gap-{sid}",
                skill_id=sid,
                skill_name=rs.skill_name,
                importance=rs.importance,
                claimed=res.claimed,
                level=EvidenceLevel(res.level),
                estimated_gain=max(0.0, round(_total(lifted, role) - base, 1)),
            )
        )
    gaps.sort(key=lambda g: (-g.estimated_gain, -g.importance, g.skill_name))

    audits = []
    for sp in core.scored:
        p = sp.project
        flags = [
            ProjectFlag(
                flag_id=flag_id_for(p.project_id, f.code),
                code=f.code,
                severity=f.severity,
                reason=f.reason,
                fix=f.fix,
                estimated_gain=flag_gain(inputs, p.project_id, f.code, role.id),
            )
            for f in sp.flags
        ]
        detected = sorted(_evidenced_skills(p))
        audits.append(
            ProjectAudit(
                project_id=p.project_id,
                title=p.title,
                kind=p.kind,
                url=p.url,
                demo_url=p.demo_url,
                score=round(sp.score, 1),
                counted_in_score=sp.counted,
                subscores=sp.subscores,
                design_subscores=sp.design_subscores,
                signals=to_project_signals(p.signals) if p.signals is not None else None,
                detected_skills=detected,
                flags=flags,
                self_reported=p.kind == "design",
                understanding=p.understanding,
                latest_quiz_id=p.latest_quiz_id,
            )
        )

    referenced = {i for c in claims for i in c.evidence_ids}
    referenced |= {i for comp in core.breakdown.components for r in comp.reasons for i in r.evidence_ids}
    evidence = [ev for eid, ev in core.registry.items.items() if eid in referenced]
    return ScoreResult(
        role_id=role.id,
        breakdown=core.breakdown,
        coverage=core.coverage,
        claims=claims,
        gaps=gaps,
        projects=audits,
        consistency=core.consistency,
        evidence=evidence,
        notes=core.notes,
    )


def skill_levels(inputs: ScoringInputs, skill_ids: list[str]) -> dict[str, tuple[EvidenceLevel, bool]]:
    """Evidence level and claimed flag for any catalogue skills, e.g. those a job posting names.

    Same evidence rules as `score` (quiz effects included), but not limited to the target role's skills.
    A skill with no claim and no evidence is `missing`.
    """
    items, claimed = _collect(inputs, _Registry(), [])
    _apply_quiz(items, inputs.projects)
    levels = _resolve(items, claimed, _role(inputs.target_role_id), dict(inputs.skill_overrides))
    return {
        sid: (EvidenceLevel(levels[sid].level), levels[sid].claimed) if sid in levels
        else (EvidenceLevel.missing, False)
        for sid in skill_ids
    }  # fmt: skip


def role_fits(inputs: ScoringInputs) -> list[RoleFit]:
    """The student scored against every catalogue role (decision N5): top 3 by total."""
    fits = []
    for role in catalogue.load_roles():
        core = _core(inputs, role)
        ranked = sorted(role.skills, key=lambda rs: (-rs.importance, rs.skill_name))
        strong = [rs.skill_name for rs in ranked if core.levels[rs.skill_id].level in VERIFIED][:3]
        gaps = sorted(
            (rs for rs in role.skills if core.levels[rs.skill_id].level not in VERIFIED),
            key=lambda rs: (-rs.importance, CREDIT[core.levels[rs.skill_id].level], rs.skill_name),
        )
        reasons = []
        if strong:
            reasons.append(
                f"{_join(strong)} {'has' if len(strong) == 1 else 'have'} solid evidence for this role"
            )
        if gaps:
            reasons.append(f"Still to evidence: {_join([rs.skill_name for rs in gaps[:2]])}")
        fits.append(
            RoleFit(
                role_id=role.id,
                role_name=role.name,
                score=core.breakdown.total,
                reasons=reasons,
                top_missing=[rs.skill_name for rs in gaps[:3]],
            )
        )
    fits.sort(key=lambda f: (-f.score, f.role_id))
    return fits[:3]


def _join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


# ---------------------------------------------------------------- what-if simulation (SCORING §7)

_SIGNAL_FIELDS = {
    "tests": {"has_tests": True},
    "ci": {"has_ci": True},
    "demo_url": {"has_demo_url": True},
    "license": {"has_license": True},
    "readme": {
        "readme_substantive": True,
        "readme_is_template": False,
        "readme_has_setup_or_screenshots": True,
    },
    "deploy_config": {"has_deploy_config": True},
}


def _find_project(projects: list[ProjectInput], project_id: str) -> ProjectInput:
    for p in projects:
        if p.project_id == project_id:
            return p
    raise SimulationError(f"unknown project '{project_id}'")


def apply_changes(inputs: ScoringInputs, changes: list[SimulationChange]) -> ScoringInputs:
    """A modified copy of the inputs. Raises SimulationError for unknown projects, flags or skills."""
    out = inputs.model_copy(deep=True)
    flag_owner = {flag_id_for(p.project_id, f.code): (p, f.code) for p in out.projects for f in _flags_for(p)}
    for change in changes:
        if change.add_signals:
            targets = (
                [_find_project(out.projects, change.project_id)]
                if change.project_id is not None
                else [p for p in out.projects if p.kind == "code" and p.signals is not None]
            )
            for p in targets:
                if p.signals is None:
                    raise SimulationError(f"project '{p.project_id}' has no repository signals to change")
                for name in change.add_signals:
                    p.signals = p.signals.model_copy(update=_SIGNAL_FIELDS[name])
                    if name == "ci":  # the CI detector would now fire for this repo
                        p.skills.setdefault("ci-cd", [DetectorHit(kind="path", detail=".github/workflows/")])
        for fid in change.resolve_flags:
            if fid not in flag_owner:
                raise SimulationError(f"unknown flag '{fid}'")
            p, code = flag_owner[fid]
            p = _find_project(out.projects, p.project_id)
            if code == "understanding_gap":
                p.understanding = Understanding.demonstrated  # SCORING §7
            else:
                p.flags = [f for f in p.flags if f.code != code]
        if change.set_understanding is not None:
            if change.project_id is None:
                raise SimulationError("set_understanding needs a project_id")
            _find_project(out.projects, change.project_id).understanding = change.set_understanding
        if change.set_skill_level is not None:
            skill, level = change.set_skill_level.skill_id, change.set_skill_level.level
            if skill is None or level is None:
                raise SimulationError("set_skill_level needs both skill_id and level")
            if catalogue.get_skill(skill) is None:
                raise SimulationError(f"unknown skill '{skill}'")
            out.skill_overrides[skill] = level.value
    return out


def simulate(
    inputs: ScoringInputs, request: SimulationRequest, role_id: str | None = None
) -> SimulationResult:
    role = _role(role_id or inputs.target_role_id)
    before = _core(inputs, role).breakdown
    after = _core(apply_changes(inputs, request.changes), role).breakdown
    return SimulationResult(before=before, after=after, delta=round(after.total - before.total, 1))


def changes_gain(inputs: ScoringInputs, changes: list[SimulationChange], role_id: str | None = None) -> float:
    """Points the changes would add (never negative): the `estimated_gain` of a gap, flag or milestone."""
    return max(0.0, simulate(inputs, SimulationRequest(changes=changes), role_id).delta)


def skill_gain(inputs: ScoringInputs, skill_id: str, role_id: str | None = None) -> float:
    change = SimulationChange(set_skill_level={"skill_id": skill_id, "level": EvidenceLevel.strong})
    return changes_gain(inputs, [change], role_id)


def flag_gain(inputs: ScoringInputs, project_id: str, code: str, role_id: str | None = None) -> float:
    """Gain from resolving one flag; for understanding_gap, as if the quiz showed understanding."""
    if code == "understanding_gap":
        change = SimulationChange(project_id=project_id, set_understanding=Understanding.demonstrated)
    else:
        change = SimulationChange(resolve_flags=[flag_id_for(project_id, code)])
    return changes_gain(inputs, [change], role_id)
