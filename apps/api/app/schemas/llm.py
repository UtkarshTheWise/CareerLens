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
