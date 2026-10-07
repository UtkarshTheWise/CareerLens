"""Input and output models of the scoring engine (docs/SCORING.md).

`ScoringInputs` holds only derived facts, never raw resume or LinkedIn text, so B6 can store it with
the analysis and re-score after a quiz or a what-if without any LLM or GitHub call.
"""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.api import (
    ConsistencySummary,
    Evidence,
    ProjectAudit,
    ScoreBreakdown,
    SkillClaim,
    SkillGap,
    Understanding,
)
from app.schemas.llm import ResumeProfile
from app.services.detectors import DetectorHit, RepoSignals
from app.services.github import WeekCount


class SimulationError(ValueError):
    """A what-if request names a project, flag or skill that does not exist."""


class FlagInput(BaseModel):
    """A low-evidence flag on a project: B4's rule flags plus B6's vague_description / claim_mismatch."""

    code: Literal[
        "single_dump",
        "unmodified_fork",
        "default_readme",
        "tutorial_pattern",
        "thin_wrapper",
        "claim_mismatch",
        "vague_description",
        "understanding_gap",
    ]
    severity: Literal["low", "medium", "high"]
    reason: str
    fix: str


class DesignInput(BaseModel):
    """DesignJudgement rubric points for one portfolio item (docs/PIPELINE.md stage 5b)."""

    readable: bool = True
    problem_statement: int = Field(default=0, ge=0, le=25)
    process_evidence: int = Field(default=0, ge=0, le=30)
    outcome_or_metrics: int = Field(default=0, ge=0, le=20)
    tool_evidence: int = Field(default=0, ge=0, le=15)
    presentation: int = Field(default=0, ge=0, le=10)
    tools_seen: list[str] = Field(default_factory=list)  # as written on the page; scoring normalises them

    @property
    def total(self) -> int:
        if not self.readable:
            return 0
        return (
            self.problem_statement
            + self.process_evidence
            + self.outcome_or_metrics
            + self.tool_evidence
            + self.presentation
        )


class ProjectInput(BaseModel):
    """One repository or one portfolio item, already matched to the resume by the pipeline."""

    project_id: str
    title: str
    kind: Literal["code", "design"] = "code"
    url: str | None = None
    demo_url: str | None = None
    signals: RepoSignals | None = None  # code projects
    skills: dict[str, list[DetectorHit]] = Field(default_factory=dict)  # detector hits by skill id
    language_skills: list[str] = Field(default_factory=list)
    claimed_skill_ids: list[str] = Field(default_factory=list)  # skills the resume names for this project
    flags: list[FlagInput] = Field(default_factory=list)
    design: DesignInput | None = None  # design items
    understanding: Understanding = Understanding.not_taken
    covered_skill_ids: list[str] = Field(default_factory=list)  # skills the latest verify quiz covered
    gap_flag: FlagInput | None = None  # optional custom text for the understanding_gap flag (from the quiz)
    latest_quiz_id: UUID | None = None


class ScoringInputs(BaseModel):
    today: date  # passed in: scoring never reads the clock
    target_role_id: str
    resume: ResumeProfile
    has_contact: bool = True  # computed from the raw text before PII stripping
    has_linkedin: bool = False
    linkedin_skill_ids: list[str] = Field(default_factory=list)  # catalogue skills found in LinkedIn text
    github_linked: bool = False
    weeks: list[WeekCount] = Field(default_factory=list)  # last 26 weeks, oldest first
    last_active_date: date | None = None
    projects: list[ProjectInput] = Field(default_factory=list)
    skill_overrides: dict[str, Literal["strong", "moderate", "weak", "unverified", "missing"]] = Field(
        default_factory=dict
    )  # what-if only: empty in stored inputs


class ScoreResult(BaseModel):
    """Everything the report needs that is computed, not written by an LLM."""

    role_id: str
    breakdown: ScoreBreakdown
    coverage: float
    claims: list[SkillClaim]
    gaps: list[SkillGap]
    projects: list[ProjectAudit]
    consistency: ConsistencySummary | None
    evidence: list[Evidence]
    notes: list[str]
