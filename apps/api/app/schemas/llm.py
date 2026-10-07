"""Small LLM response schemas from docs/PIPELINE.md. One small object per call.

Keep them flat and free-form-object-free: they are sent to Gemini as a JSON schema and to
Groq in strict mode (services.llm.to_strict_schema).
"""

from pydantic import BaseModel, Field


class ResumeEducation(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    start: str | None = None
    end: str | None = None
    grade: str | None = None


class ResumeExperience(BaseModel):
    org: str
    role: str
    start: str | None = None
    end: str | None = None
    bullets: list[str] = Field(default_factory=list)
    mentioned_technologies: list[str] = Field(default_factory=list)


class ResumeProject(BaseModel):
    title: str
    description: str
    links: list[str] = Field(default_factory=list)
    mentioned_technologies: list[str] = Field(default_factory=list)


class ResumeCertification(BaseModel):
    name: str
    issuer: str | None = None


class ResumeProfile(BaseModel):
    """Stage 2 output: only what is literally written on the resume."""

    headline: str | None = None
    education: list[ResumeEducation] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience: list[ResumeExperience] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    certifications: list[ResumeCertification] = Field(default_factory=list)
    page_count_hint: int | None = None


class JudgementIssue(BaseModel):
    issue: str
    fix: str  # something the student can do in under a day


class ProjectJudgement(BaseModel):
    """Stage 5a: judges only the DESCRIPTION's specificity and its consistency with measured facts."""

    what_it_does: str  # one plain sentence, from the facts only
    has_metric: bool
    has_architecture_detail: bool
    specificity: int = Field(ge=0, le=3)
    buzzwords: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(
        default_factory=list
    )  # claimed technologies not visible in the facts
    issues: list[JudgementIssue] = Field(default_factory=list)
    honest_rewrite: str  # <= 2 lines, uses only the given facts, no new numbers


class DesignJudgement(BaseModel):
    """Stage 5b: the portfolio rubric, scored strictly from what is on the page."""

    readable: bool
    problem_statement: int = Field(ge=0, le=25)
    process_evidence: int = Field(ge=0, le=30)
    outcome_or_metrics: int = Field(ge=0, le=20)
    tool_evidence: int = Field(ge=0, le=15)
    presentation: int = Field(ge=0, le=10)
    tools_seen: list[str] = Field(default_factory=list)
    issues: list[JudgementIssue] = Field(default_factory=list)


class RoadmapMilestonePlan(BaseModel):
    title: str
    deliverable: str  # a concrete thing that produces new evidence
    addresses: list[str] = Field(default_factory=list)  # gap ids and flag ids from the prompt
    resource_ids: list[str] = Field(default_factory=list)  # ids from the catalogue in the prompt
    effort_hours: int = Field(ge=1, le=200)


class RoadmapPlan(BaseModel):
    """Stage 7: the model only chooses ids and writes deliverables; Python attaches URLs and gains."""

    milestones: list[RoadmapMilestonePlan] = Field(default_factory=list)


class JobPostingExtract(BaseModel):
    """Job page fallback (docs/PIPELINE.md): only what is written on the page."""

    title: str
    company: str | None = None
    location: str | None = None
    employment_type: str | None = None
    experience_years_min: int | None = Field(default=None, ge=0, le=50)
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    deadline: str | None = None  # ISO date (YYYY-MM-DD) if the page gives one
