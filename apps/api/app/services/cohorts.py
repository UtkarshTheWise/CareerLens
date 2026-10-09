"""Cohort metrics for the placement cell (docs/SCORING.md section 8).

Everything is computed in Python from stored analyses, so it behaves the same on SQLite and Postgres and
never calls an LLM. `load_rows` reads the data; `aggregate`, `students` and `to_csv` are pure.
A student whose latest analysis is for another role is re-scored for the requested role from the stored
scoring inputs (pure, no LLM, no GitHub), so one analysis serves every role view.
"""

import csv
import io
import statistics
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.schemas.api import (
    AnalysisReport,
    Band,
    BandCounts,
    BuiltAndExplainedRate,
    CohortInsights,
    CohortStudent,
    CohortUnderstanding,
    DepartmentStat,
    EvidenceLevel,
    HistogramBucket,
    MatchedSkill,
    MissingSkillCount,
    ProjectAudit,
    SkillClaim,
    SkillGap,
    Understanding,
    UnverifiedRate,
)
from app.services import scoring
from app.services.scoring_inputs import ScoringInputs

AT_RISK_SCORE = 50
AT_RISK_COVERAGE = 40
TOP_N = 10
MIN_CLAIMANTS = 2  # a rate over a single student says nothing about the cohort
VERIFIED = {EvidenceLevel.strong, EvidenceLevel.moderate}
UNBACKED = {EvidenceLevel.weak, EvidenceLevel.unverified}
LEVEL_RANK = {
    EvidenceLevel.missing: 0,
    EvidenceLevel.unverified: 1,
    EvidenceLevel.weak: 2,
    EvidenceLevel.moderate: 3,
    EvidenceLevel.strong: 4,
}
StudentSort = Literal["score_asc", "score_desc", "coverage_desc", "name"]
BUCKETS = [f"{lo}-{lo + 9}" for lo in range(0, 90, 10)] + ["90-100"]


@dataclass
class Row:
    """One analysed student, as seen for one role."""

    profile: models.Profile
    analysis_id: str
    score: float
    band: Band
    coverage: float
    claims: list[SkillClaim] = field(default_factory=list)
    gaps: list[SkillGap] = field(default_factory=list)
    projects: list[ProjectAudit] = field(default_factory=list)

    @property
    def at_risk(self) -> bool:
        return self.score < AT_RISK_SCORE or self.coverage < AT_RISK_COVERAGE

    @property
    def top_project(self) -> ProjectAudit | None:
        counted = [p for p in self.projects if p.counted_in_score]
        return max(counted, key=lambda p: (p.score, p.project_id), default=None)

    @property
    def understanding(self) -> Understanding:
        top = self.top_project
        return top.understanding if top else Understanding.not_taken


def _r1(x: float) -> float:
    return round(x + 0.0, 1)


def _median(values: list[float]) -> float | None:
    return _r1(statistics.median(values)) if values else None


# ---------------------------------------------------------------- reading


def latest_done_analysis(db: Session, profile_id: str) -> models.Analysis | None:
    return db.scalar(
        select(models.Analysis)
        .where(
            models.Analysis.profile_id == profile_id,
            models.Analysis.status == "done",
            models.Analysis.report.is_not(None),
        )
        .order_by(models.Analysis.created_at.desc(), models.Analysis.id)
        .limit(1)
    )


def _row(profile: models.Profile, analysis: models.Analysis, role_id: str) -> Row:
    if analysis.role_id == role_id or not analysis.signals:
        report = AnalysisReport.model_validate(analysis.report)
        return Row(
            profile, analysis.id, report.score.total, report.score.band, report.coverage,
            report.claims, report.gaps, report.projects,
        )  # fmt: skip
    result = scoring.score(ScoringInputs.model_validate(analysis.signals), role_id)
    return Row(
        profile, analysis.id, result.breakdown.total, result.breakdown.band, result.coverage,
        result.claims, result.gaps, result.projects,
    )  # fmt: skip


def load_rows(db: Session, cohort_id: str, role_id: str) -> tuple[list[Row], list[models.Profile]]:
    """The cohort's analysed students for a role, and all its profiles."""
    profiles = list(
        db.scalars(
            select(models.Profile).where(models.Profile.cohort_id == cohort_id).order_by(models.Profile.id)
        )
    )
    rows = []
    for profile in profiles:
        analysis = latest_done_analysis(db, profile.id)
        if analysis is not None:
            rows.append(_row(profile, analysis, role_id))
    return rows, profiles


# ---------------------------------------------------------------- insights


def _histogram(scores: list[float]) -> list[HistogramBucket]:
    counts = [0] * len(BUCKETS)
    for s in scores:
        counts[min(int(s // 10), 9)] += 1
    return [HistogramBucket(bucket=b, count=c) for b, c in zip(BUCKETS, counts, strict=True)]


def _top_missing(rows: list[Row]) -> list[MissingSkillCount]:
    counts: dict[str, tuple[str, int]] = {}
    for row in rows:
        for claim in row.claims:
            if claim.level == EvidenceLevel.missing:
                name, n = counts.get(claim.skill_id, (claim.skill_name, 0))
                counts[claim.skill_id] = (name, n + 1)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1][1], kv[1][0]))[:TOP_N]
    return [MissingSkillCount(skill_id=sid, skill_name=name, students=n) for sid, (name, n) in ranked]


def _claimants(rows: list[Row]) -> dict[str, tuple[str, list[tuple[Row, SkillClaim]]]]:
    by_skill: dict[str, tuple[str, list[tuple[Row, SkillClaim]]]] = {}
    for row in rows:
        for claim in row.claims:
            if claim.claimed:
                by_skill.setdefault(claim.skill_id, (claim.skill_name, []))[1].append((row, claim))
    return {sid: v for sid, v in by_skill.items() if len(v[1]) >= MIN_CLAIMANTS}


def _unverified_rates(claimants: dict) -> list[UnverifiedRate]:
    rates = []
    for sid, (name, pairs) in claimants.items():
        unbacked = sum(1 for _, c in pairs if c.level in UNBACKED)
        rates.append(UnverifiedRate(
            skill_id=sid, skill_name=name, claimed_by=len(pairs),
            unverified_rate=_r1(100 * unbacked / len(pairs)),
        ))  # fmt: skip
    rates.sort(key=lambda r: (-r.unverified_rate, -r.claimed_by, r.skill_name))
    return rates[:TOP_N]


def _explained(row: Row, skill_id: str) -> bool:
    """A project that backs the skill and whose verify quiz showed understanding."""
    return any(
        p.understanding == Understanding.demonstrated and skill_id in p.detected_skills for p in row.projects
    )


def _understanding(rows: list[Row], claimants: dict) -> CohortUnderstanding:
    seen = [r.understanding for r in rows]
    summary = CohortUnderstanding(
        quizzed=sum(1 for u in seen if u != Understanding.not_taken),
        demonstrated=seen.count(Understanding.demonstrated),
        partial=seen.count(Understanding.partial),
        not_demonstrated=seen.count(Understanding.not_demonstrated),
    )
    if summary.quizzed == 0:
        return summary
    rates = []
    for sid, (name, pairs) in claimants.items():
        both = sum(1 for row, claim in pairs if claim.level in VERIFIED and _explained(row, sid))
        rates.append(
            BuiltAndExplainedRate(
                skill_id=sid,
                skill_name=name,
                claimed_by=len(pairs),
                built_and_explained_rate=_r1(100 * both / len(pairs)),
            )
        )
    rates.sort(key=lambda r: (-r.claimed_by, r.skill_name))
    summary.by_skill = rates[:TOP_N]
    return summary


def _by_department(rows: list[Row], profiles: list[models.Profile]) -> list[DepartmentStat]:
    students: dict[str, int] = defaultdict(int)
    scores: dict[str, list[float]] = defaultdict(list)
    for p in profiles:
        if p.department:
            students[p.department] += 1
    for row in rows:
        if row.profile.department:
            scores[row.profile.department].append(row.score)
    return [
        DepartmentStat(department=d, students=n, median_score=_median(scores[d]))
        for d, n in sorted(students.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def aggregate(
    rows: list[Row], profiles: list[models.Profile], cohort_id: str, role_id: str
) -> CohortInsights:
    scores = [r.score for r in rows]
    claimants = _claimants(rows)
    return CohortInsights(
        cohort_id=cohort_id,
        role_id=role_id,
        student_count=len(profiles),
        analysed_count=len(rows),
        median_score=_median(scores),
        median_coverage=_median([r.coverage for r in rows]),
        bands=BandCounts(
            not_ready=sum(1 for r in rows if r.band == Band.not_ready),
            developing=sum(1 for r in rows if r.band == Band.developing),
            ready=sum(1 for r in rows if r.band == Band.ready),
        ),
        histogram=_histogram(scores),
        top_missing_skills=_top_missing(rows),
        unverified_rate_by_skill=_unverified_rates(claimants),
        at_risk_count=sum(1 for r in rows if r.at_risk),
        understanding=_understanding(rows, claimants),
        by_department=_by_department(rows, profiles),
    )


# ---------------------------------------------------------------- students and export


@dataclass(frozen=True)
class StudentQuery:
    """Filters for the student list (docs/SCORING.md section 8). Defaults reproduce the unfiltered list."""

    at_risk_only: bool = False
    skills: tuple[str, ...] = ()
    skill_match: Literal["all", "any"] = "all"
    min_level: EvidenceLevel = EvidenceLevel.moderate  # moderate = strong or moderate evidence
    min_score: float | None = None
    bands: frozenset[Band] = frozenset()
    sort: StudentSort = "score_asc"
    limit: int | None = None


def matched_skills(row: Row, skills: Sequence[str], min_level: EvidenceLevel) -> list[MatchedSkill]:
    """The requested skills this student has at `min_level` or better, in request order.

    Only skills the role requires or the student claims have a claim row, so any other id never matches.
    """
    by_id = {c.skill_id: c for c in row.claims}
    found = []
    for skill_id in skills:
        claim = by_id.get(skill_id)
        if claim is not None and LEVEL_RANK[claim.level] >= LEVEL_RANK[min_level]:
            found.append(MatchedSkill(skill_id=skill_id, skill_name=claim.skill_name, level=claim.level))
    return found


def _passes(row: Row, query: StudentQuery, matched: list[MatchedSkill]) -> bool:
    if query.at_risk_only and not row.at_risk:
        return False
    if query.min_score is not None and row.score < query.min_score:
        return False
    if query.bands and row.band not in query.bands:
        return False
    if query.skills:
        needed = len(query.skills) if query.skill_match == "all" else 1
        if len(matched) < needed:
            return False
    return True


def _sort_key(sort: StudentSort) -> Callable[[Row], tuple]:
    if sort == "score_desc":
        return lambda r: (-r.score, r.profile.name, r.profile.id)
    if sort == "coverage_desc":
        return lambda r: (-r.coverage, -r.score, r.profile.name, r.profile.id)
    if sort == "name":
        return lambda r: (r.profile.name.casefold(), r.profile.id)
    return lambda r: (r.score, r.profile.name, r.profile.id)  # score_asc: weakest first, the default


def students(rows: list[Row], query: StudentQuery = StudentQuery()) -> list[CohortStudent]:
    """Filtered, sorted, limited. Weakest first by default, so the students who need help are at the top."""
    skills = tuple(dict.fromkeys(query.skills))  # request order, no repeats
    matches = {r.profile.id: matched_skills(r, skills, query.min_level) for r in rows}
    picked = [r for r in rows if _passes(r, query, matches[r.profile.id])]
    picked.sort(key=_sort_key(query.sort))
    if query.limit is not None:
        picked = picked[: query.limit]
    return [
        CohortStudent(
            profile_id=r.profile.id,
            name=r.profile.name,
            github_username=r.profile.github_username,
            analysis_id=r.analysis_id,
            department=r.profile.department,
            score=r.score,
            band=r.band,
            coverage=r.coverage,
            top_gap=r.gaps[0].skill_name if r.gaps else None,
            at_risk=r.at_risk,
            understanding=r.understanding,
            matched_skills=matches[r.profile.id],
        )
        for r in picked
    ]


CSV_COLUMNS = [
    "profile_id", "name", "github_username", "department", "score", "band", "coverage", "top_gap", "at_risk",
    "understanding", "matched_skills",
]  # fmt: skip


def _safe(value: object) -> object:
    """Stop spreadsheet apps from running a cell as a formula (CSV injection)."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def to_csv(rows: list[CohortStudent]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    for s in rows:
        data = s.model_dump(mode="json")
        matched = data["matched_skills"]
        data["matched_skills"] = "; ".join(f"{m['skill_name']} ({m['level']})" for m in matched)
        writer.writerow([_safe(data[c]) for c in CSV_COLUMNS])
    return out.getvalue()
