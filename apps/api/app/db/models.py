"""Tables for the prototype.

Ids are UUID strings so the same models run on SQLite and Postgres.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.base import Base


class UtcDateTime(TypeDecorator):
    """Timezone-aware UTC datetimes on every backend (SQLite hands back naive values)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC) if value is not None else None

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Cohort(Base):
    __tablename__ = "cohorts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(100))
    year: Mapped[int | None] = mapped_column(Integer)

    profiles: Mapped[list["Profile"]] = relationship(back_populates="cohort")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Subject of the auth token; null for seeded students. The demo profile uses "dev".
    auth_subject: Mapped[str | None] = mapped_column(String(200), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    github_username: Mapped[str | None] = mapped_column(String(100))
    portfolio_urls: Mapped[list[str]] = mapped_column(JSON, default=list)
    linkedin_text: Mapped[str | None] = mapped_column(Text)
    target_role_id: Mapped[str | None] = mapped_column(String(64))
    department: Mapped[str | None] = mapped_column(String(100))
    cohort_id: Mapped[str | None] = mapped_column(ForeignKey("cohorts.id", ondelete="SET NULL"), index=True)
    # Per-project understanding from verify quizzes, keyed by repo or portfolio URL (docs/QUIZ.md §5).
    project_understanding: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    latest_analysis_id: Mapped[str | None] = mapped_column(String(36))
    latest_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)

    cohort: Mapped[Cohort | None] = relationship(back_populates="profiles")
    documents: Mapped[list["Document"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    quizzes: Mapped[list["Quiz"]] = relationship(back_populates="profile", cascade="all, delete-orphan")

    @property
    def has_resume(self) -> bool:
        return any(d.kind == "resume" for d in self.documents)

    @property
    def has_linkedin(self) -> bool:
        return bool(self.linkedin_text) or any(d.kind == "linkedin" for d in self.documents)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # resume | linkedin
    filename: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text, default="")
    page_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)

    profile: Mapped[Profile] = relationship(back_populates="documents")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    coverage: Mapped[float | None] = mapped_column(Float)
    verified_skills: Mapped[int | None] = mapped_column(Integer)
    report: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # AnalysisReport JSON
    signals: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # stored inputs for simulate / re-score
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime)

    profile: Mapped[Profile] = relationship(back_populates="analyses")
    quizzes: Mapped[list["Quiz"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    company: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="saved")
    deadline: Mapped[str | None] = mapped_column(String(10))  # ISO date
    keyword_match: Mapped[float | None] = mapped_column(Float)
    evidence_match: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    applied_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, onupdate=utcnow)

    profile: Mapped[Profile] = relationship(back_populates="applications")


class Quiz(Base):
    """A Project Understanding Check (docs/QUIZ.md): one project, one attempt."""

    __tablename__ = "quizzes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(String(200))
    project_title: Mapped[str] = mapped_column(String(300))
    project_url: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(10), default="code")  # code | design
    mode: Mapped[str] = mapped_column(String(10))  # practice | verify
    status: Mapped[str] = mapped_column(String(20), default="in_progress")  # in_progress | submitted
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    auto_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    abandoned: Mapped[bool] = mapped_column(Boolean, default=False)  # never started: no effect on evidence
    score: Mapped[float | None] = mapped_column(Float)
    understanding: Mapped[str | None] = mapped_column(String(20))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # the QuizResult returned by submit
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(UtcDateTime)

    profile: Mapped[Profile] = relationship(back_populates="quizzes")
    analysis: Mapped[Analysis] = relationship(back_populates="quizzes")
    questions: Mapped[list["QuizQuestion"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan", order_by="QuizQuestion.order"
    )


class QuizQuestion(Base):
    """A question with its answer key. The key columns are never put in a response before grading."""

    __tablename__ = "quiz_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), index=True)
    order: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(20))  # mcq | short_answer
    category: Mapped[str] = mapped_column(String(30))
    prompt: Mapped[str] = mapped_column(Text)
    code_snippet: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    hint: Mapped[str | None] = mapped_column(Text)
    skill_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    time_limit_s: Mapped[int | None] = mapped_column(Integer)
    served_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    # answer key (server side only until graded)
    source_ref: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    correct_choice_id: Mapped[str | None] = mapped_column(String(10))
    key_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    acceptable_alternatives: Mapped[list[str]] = mapped_column(JSON, default=list)
    model_answer: Mapped[str | None] = mapped_column(Text)
    grading_context: Mapped[str | None] = mapped_column(Text)  # the cited code or page text, for the grader

    quiz: Mapped[Quiz] = relationship(back_populates="questions")
    answer: Mapped["QuizAnswer | None"] = relationship(
        back_populates="question", cascade="all, delete-orphan", uselist=False
    )


class QuizAnswer(Base):
    """What the student answered. Focus-loss counts live here only: no cohort code reads this table."""

    __tablename__ = "quiz_answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    question_id: Mapped[str] = mapped_column(
        ForeignKey("quiz_questions.id", ondelete="CASCADE"), unique=True, index=True
    )
    choice_id: Mapped[str | None] = mapped_column(String(10))
    text: Mapped[str | None] = mapped_column(Text)
    time_taken_ms: Mapped[int] = mapped_column(Integer, default=0)
    focus_lost_count: Mapped[int] = mapped_column(Integer, default=0)
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False)
    answered_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    # grading (set when graded)
    score: Mapped[float | None] = mapped_column(Float)  # 0-1
    key_results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    incorrect_statements: Mapped[list[str]] = mapped_column(JSON, default=list)
    feedback: Mapped[str | None] = mapped_column(Text)

    question: Mapped[QuizQuestion] = relationship(back_populates="answer")


class CacheEntry(Base):
    """Cache of every external call (LLM, GitHub), keyed by sha256 of its inputs."""

    __tablename__ = "cache"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # llm | github | http
    value: Mapped[Any] = mapped_column(JSON)
    is_json: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
