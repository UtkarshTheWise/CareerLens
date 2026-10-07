"""Pydantic models mirroring contracts/openapi.yaml (v0.2.0) EXACTLY.

Same schema names, property names, required lists and enums as the contract;
scripts/check_contract.py enforces it. A field is "required" here iff it has no default.
Objects the contract declares inline get a helper model (RoleSkill, ScoreReason, ...);
those names are not part of the contract.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Error(ApiModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class HealthResponse(ApiModel):
    status: Literal["ok"]
    version: str
    llm_provider: str | None = None


# ---------- catalogue ----------
class RoleSkill(ApiModel):
    skill_id: str
    skill_name: str
    importance: int = Field(ge=1, le=3)


class Role(ApiModel):
    id: str
    name: str
    category: Literal["engineering", "data", "design", "product"]
    skills: list[RoleSkill]


class Resource(ApiModel):
    id: str
    title: str
    url: str
    type: Literal["course", "documentation", "video", "practice", "project_idea"]
    skill_id: str
    hours: int | None = None


# ---------- profiles ----------
class ProfileCreate(ApiModel):
    name: str
    email: str | None = None
    github_username: str | None = None
    portfolio_urls: list[str] = Field(default_factory=list)
    linkedin_text: str | None = None
    target_role_id: str | None = None
    department: str | None = None
    cohort_id: UUID | None = None


class ProfileUpdate(ApiModel):
    name: str | None = None
    github_username: str | None = None
    portfolio_urls: list[str] | None = None
    linkedin_text: str | None = None
    target_role_id: str | None = None
    department: str | None = None
    cohort_id: UUID | None = None


class Profile(ProfileCreate):
    id: UUID
    has_resume: bool
    has_linkedin: bool
    latest_analysis_id: UUID | None = None
    latest_score: float | None = None
    created_at: datetime


# ---------- analyses ----------
class AnalysisStage(StrEnum):
    queued = "queued"
    ingesting = "ingesting"
    extracting = "extracting"
    collecting = "collecting"
    detecting = "detecting"
    judging = "judging"
    scoring = "scoring"
    planning = "planning"
    done = "done"
    failed = "failed"


class Band(StrEnum):
    not_ready = "not_ready"
    developing = "developing"
    ready = "ready"


class Confidence(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class EvidenceLevel(StrEnum):
    strong = "strong"
    moderate = "moderate"
    weak = "weak"
    unverified = "unverified"
    missing = "missing"


class Understanding(StrEnum):
    not_taken = "not_taken"
    demonstrated = "demonstrated"
    partial = "partial"
    not_demonstrated = "not_demonstrated"


class QuizMode(StrEnum):
    practice = "practice"
    verify = "verify"


class QuizStatus(StrEnum):
    in_progress = "in_progress"
    submitted = "submitted"


class ApplicationStatus(StrEnum):
    saved = "saved"
    applied = "applied"
    interviewing = "interviewing"
    offer = "offer"
    rejected = "rejected"


class ScoreReason(ApiModel):
    text: str
    delta: float
    evidence_ids: list[str] = Field(default_factory=list)


class ScoreComponent(ApiModel):
    key: Literal["skill_evidence", "project_quality", "consistency", "experience", "resume_quality"]
    label: str
    weight: float
    score: float | None
    contribution: float
    reasons: list[ScoreReason]


class ScoreBreakdown(ApiModel):
    total: float = Field(ge=0, le=100)
    band: Band
    confidence: Confidence
    capped: bool = False
    components: list[ScoreComponent]


class Evidence(ApiModel):
    id: str
    kind: Literal[
        "repo",
        "file",
        "commit_range",
        "portfolio_item",
        "experience",
        "resume_text",
        "linkedin",
        "certificate",
    ]
    source: Literal["github", "resume", "linkedin", "portfolio"]
    label: str
    url: str | None = None
    details: dict[str, Any] | None = None


class SkillClaim(ApiModel):
    skill_id: str
    skill_name: str
    claimed: bool
    level: EvidenceLevel
    reason: str
    evidence_ids: list[str]


class SkillGap(ApiModel):
    gap_id: str
    skill_id: str
    skill_name: str
    importance: int = Field(ge=1, le=3)
    claimed: bool
    level: EvidenceLevel
    estimated_gain: float


class ProjectFlag(ApiModel):
    flag_id: str
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
    estimated_gain: float


class ProjectSubscores(ApiModel):
    hygiene: float = 0
    engineering: float = 0
    authorship: float = 0
    depth: float = 0


class DesignSubscores(ApiModel):
    problem_statement: float = 0
    process_evidence: float = 0
    outcome_or_metrics: float = 0
    tool_evidence: float = 0
    presentation: float = 0


class ProjectSignals(ApiModel):
    tests: bool
    ci: bool
    demo_url: bool
    license: bool
    readme: bool
    deploy_config: bool
    authored_commits: int
    total_commits: int


class ProjectIssue(ApiModel):
    issue: str
    fix: str


class ProjectAudit(ApiModel):
    project_id: str
    title: str
    kind: Literal["code", "design"]
    url: str | None = None
    demo_url: str | None = None
    score: float = Field(ge=0, le=100)
    counted_in_score: bool
    subscores: ProjectSubscores | None = None
    design_subscores: DesignSubscores | None = None
    signals: ProjectSignals | None = None
    detected_skills: list[str]
    what_it_does: str | None = None
    honest_rewrite: str | None = None
    issues: list[ProjectIssue] = Field(default_factory=list)
    flags: list[ProjectFlag]
    self_reported: bool
    understanding: Understanding = Understanding.not_taken
    latest_quiz_id: UUID | None = None


class RoleFit(ApiModel):
    role_id: str
    role_name: str
    score: float
    reasons: list[str]
    top_missing: list[str]


class RoadmapMilestone(ApiModel):
    id: str
    order: int
    title: str
    deliverable: str
    addresses: list[str]
    resources: list[Resource]
    effort_hours: int
    estimated_gain: float
    done: bool = False


class WeekCount(ApiModel):
    week_start: date
    count: int


class ConsistencySummary(ApiModel):
    weeks: list[WeekCount]
    active_weeks: int
    cv: float | None = None
    last_active_date: date | None = None
    score: float


class AnalysisReport(ApiModel):
    score: ScoreBreakdown
    coverage: float = Field(ge=0, le=100)
    claims: list[SkillClaim]
    gaps: list[SkillGap]
    projects: list[ProjectAudit]
    role_fits: list[RoleFit] = Field(max_length=3)
    roadmap: list[RoadmapMilestone]
    consistency: ConsistencySummary | None = None
    evidence: list[Evidence]
    notes: list[str]


class AnalysisStatus(ApiModel):
    id: UUID
    profile_id: UUID
    role_id: str
    status: AnalysisStage
    progress: int = Field(ge=0, le=100)
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class AnalysisSummary(ApiModel):
    id: UUID
    role_id: str
    status: AnalysisStage
    score: float | None = None
    coverage: float | None = None
    verified_skills: int | None = None
    created_at: datetime


class Analysis(AnalysisStatus):
    report: AnalysisReport | None = None


class AnalysisStart(ApiModel):
    """Inline request body of startAnalysis."""

    role_id: str
    force_refresh: bool = False


class MilestoneUpdate(ApiModel):
    """Inline request body of updateMilestone."""

    done: bool


SimulationSignal = Literal["tests", "ci", "demo_url", "license", "readme", "deploy_config"]


class SkillLevelChange(ApiModel):
    skill_id: str | None = None
    level: EvidenceLevel | None = None


class SimulationChange(ApiModel):
    project_id: str | None = None
    add_signals: list[SimulationSignal] = Field(default_factory=list)
    resolve_flags: list[str] = Field(default_factory=list)
    set_understanding: Understanding | None = None
    set_skill_level: SkillLevelChange | None = None


class SimulationRequest(ApiModel):
    changes: list[SimulationChange]


class SimulationResult(ApiModel):
    before: ScoreBreakdown
    after: ScoreBreakdown
    delta: float


# ---------- quizzes (docs/QUIZ.md) ----------
class SourceRef(ApiModel):
    path: str
    start_line: int | None = None
    end_line: int | None = None
    section: str | None = None
    url: str | None = None


class QuizCreate(ApiModel):
    project_id: str
    mode: QuizMode
    question_count: int | None = Field(default=None, ge=3, le=10)


class CodeSnippet(ApiModel):
    path: str
    start_line: int
    end_line: int
    code: str
    language: str | None = None


class QuizOption(ApiModel):
    id: str
    text: str


class QuizQuestion(ApiModel):
    id: str
    order: int
    type: Literal["mcq", "short_answer"]
    category: Literal[
        "code_reading",
        "architecture",
        "design_decision",
        "debugging",
        "extension",
        "claim_check",
        "process",
        "outcome",
        "critique",
    ]
    prompt: str
    code_snippet: CodeSnippet | None = None
    options: list[QuizOption] = Field(default_factory=list)
    hint: str | None = None
    time_limit_s: int | None = None
    served_at: datetime | None = None
    time_remaining_s: int | None = None
    answered: bool = False
    skill_ids: list[str]


class Quiz(ApiModel):
    id: UUID
    analysis_id: UUID
    project_id: str
    project_title: str
    mode: QuizMode
    status: QuizStatus
    total_questions: int
    questions: list[QuizQuestion]
    created_at: datetime


class QuizAnswer(ApiModel):
    question_id: str
    choice_id: str | None = None
    text: str | None = Field(default=None, max_length=2000)
    time_taken_ms: int
    focus_lost_count: int = 0


class KeyPointResult(ApiModel):
    text: str
    status: Literal["covered", "partial", "missing"]


class QuizAnswerFeedback(ApiModel):
    question_id: str
    recorded: bool
    timed_out: bool = False
    choice_id: str | None = None
    text: str | None = None
    score: float | None = None
    correct_choice_id: str | None = None
    key_points: list[KeyPointResult] = Field(default_factory=list)
    incorrect_statements: list[str] = Field(default_factory=list)
    feedback: str | None = None
    model_answer: str | None = None
    source_ref: SourceRef | None = None


class ReviewTopic(ApiModel):
    topic: str
    source_ref: SourceRef | None = None


class QuizResult(ApiModel):
    quiz_id: UUID
    mode: QuizMode
    score: float = Field(ge=0, le=100)
    understanding: Understanding | None
    per_question: list[QuizAnswerFeedback]
    strengths: list[str]
    review_topics: list[ReviewTopic]
    focus_lost_total: int | None = None
    flag: ProjectFlag | None = None
    score_update: SimulationResult | None = None
    retake_available_at: datetime | None = None


class QuizSummary(ApiModel):
    id: UUID
    project_id: str
    project_title: str
    mode: QuizMode
    status: QuizStatus
    score: float | None = None
    understanding: Understanding | None = None
    created_at: datetime


# ---------- jobs & applications ----------
class JobPosting(ApiModel):
    title: str
    company: str | None = None
    location: str | None = None
    url: str | None = None
    description: str = Field(max_length=20000)
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    deadline: date | None = None
    source: Literal["jsonld", "dom", "llm", "manual"]


class JobMatchRequest(ApiModel):
    """Inline request body of matchJob."""

    profile_id: UUID
    posting: JobPosting


class MatchedSkill(ApiModel):
    skill_id: str
    skill_name: str
    level: EvidenceLevel


class JobMatch(ApiModel):
    keyword_match: float = Field(ge=0, le=100)
    evidence_match: float = Field(ge=0, le=100)
    matched: list[MatchedSkill]
    missing: list[str]
    unverified: list[str]
    summary: str
    normalized_posting: JobPosting | None = None


class ApplicationCreate(ApiModel):
    profile_id: UUID
    company: str
    title: str
    url: str | None = None
    status: ApplicationStatus | None = None
    deadline: date | None = None
    keyword_match: float | None = None
    evidence_match: float | None = None
    description: str | None = None
    notes: str | None = None


class ApplicationUpdate(ApiModel):
    status: ApplicationStatus | None = None
    deadline: date | None = None
    notes: str | None = None
    applied_at: datetime | None = None


class Application(ApplicationCreate):
    id: UUID
    status: ApplicationStatus
    applied_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TailoredBullet(ApiModel):
    original: str
    rewritten: str
    evidence_ids: list[str] = Field(default_factory=list)


class TailoredResume(ApiModel):
    bullets: list[TailoredBullet]
    numbers_without_evidence: list[str]
    skills_order: list[str]


# ---------- cohorts ----------
class Cohort(ApiModel):
    id: UUID
    name: str
    department: str | None = None
    year: int | None = None
    student_count: int


class BandCounts(ApiModel):
    not_ready: int
    developing: int
    ready: int


class HistogramBucket(ApiModel):
    bucket: str
    count: int


class MissingSkillCount(ApiModel):
    skill_id: str
    skill_name: str
    students: int


class UnverifiedRate(ApiModel):
    skill_id: str
    skill_name: str
    claimed_by: int
    unverified_rate: float = Field(ge=0, le=100)


class BuiltAndExplainedRate(ApiModel):
    skill_id: str
    skill_name: str
    claimed_by: int
    built_and_explained_rate: float = Field(ge=0, le=100)


class CohortUnderstanding(ApiModel):
    quizzed: int
    demonstrated: int
    partial: int
    not_demonstrated: int
    by_skill: list[BuiltAndExplainedRate] = Field(default_factory=list)


class DepartmentStat(ApiModel):
    department: str
    students: int
    median_score: float | None


class CohortInsights(ApiModel):
    cohort_id: UUID
    role_id: str
    student_count: int
    analysed_count: int
    median_score: float | None
    median_coverage: float | None = None
    bands: BandCounts
    histogram: list[HistogramBucket]
    top_missing_skills: list[MissingSkillCount]
    unverified_rate_by_skill: list[UnverifiedRate]
    at_risk_count: int
    understanding: CohortUnderstanding | None = None
    by_department: list[DepartmentStat] = Field(default_factory=list)


class CohortStudent(ApiModel):
    profile_id: UUID
    name: str
    github_username: str | None = None
    analysis_id: UUID | None = None
    department: str | None = None
    score: float
    band: Band
    coverage: float
    top_gap: str | None = None
    at_risk: bool
    understanding: Understanding | None = None
