"""Builders for scoring tests: small, explicit inputs so every expected number can be checked by hand."""

from datetime import date, timedelta

from app.schemas.llm import (
    ResumeCertification,
    ResumeEducation,
    ResumeExperience,
    ResumeProfile,
    ResumeProject,
)
from app.services.detectors import DetectorHit, RepoSignals
from app.services.github import WeekCount
from app.services.scoring import project_id_for
from app.services.scoring_inputs import DesignInput, FlagInput, ProjectInput, ScoringInputs

TODAY = date(2026, 10, 7)

# Every item of SCORING §2B satisfied: scores exactly 100.
PERFECT = {
    "readme_substantive": True,
    "has_description": True,
    "has_license": True,
    "has_demo_url": True,
    "readme_has_setup_or_screenshots": True,
    "has_tests": True,
    "has_ci": True,
    "has_manifest": True,
    "has_lockfile": True,
    "module_count": 2,
    "has_deploy_config": True,
    "authored_commits": 30,
    "total_commits": 40,
    "authored_share": 0.75,
    "active_span_weeks": 4,
    "code_kb": 20,
}


def sig(**kw) -> RepoSignals:
    """Signals of a plain repo: 20 of 20 commits are the student's, nothing else present."""
    base = {"commit_facts_known": True, "authored_commits": 20, "total_commits": 20, "authored_share": 1.0}
    return RepoSignals(**{**base, **kw})


def hit(kind: str = "pip", detail: str = "pkg") -> DetectorHit:
    return DetectorHit(kind=kind, detail=detail)


def flag(code: str = "single_dump") -> FlagInput:
    return FlagInput(code=code, severity="medium", reason=f"reason for {code}", fix=f"fix for {code}")


def code_project(title: str = "campus-api", skills=(), languages=(), **kw) -> ProjectInput:
    signals = kw.pop("signals", None) or sig()
    return ProjectInput(
        project_id=project_id_for(title),
        title=title,
        kind="code",
        url=f"https://github.com/u/{title}",
        signals=signals,
        skills={s: [hit()] for s in skills},
        language_skills=list(languages),
        **kw,
    )


def design_project(title: str = "Transit app case study", **kw) -> ProjectInput:
    design = kw.pop(
        "design",
        DesignInput(
            problem_statement=20, process_evidence=20, outcome_or_metrics=10, tool_evidence=10, presentation=10,
            tools_seen=["Figma"],
        ),
    )  # fmt: skip
    return ProjectInput(
        project_id=project_id_for(title),
        title=title,
        kind="design",
        url=f"https://example.dev/{title.lower().replace(' ', '-')}",
        design=design,
        **kw,
    )


def resume(**kw) -> ResumeProfile:
    return ResumeProfile(**kw)


def experience(
    *bullets: str, org: str = "Northwind Labs", role: str = "Backend Intern", **kw
) -> ResumeExperience:
    return ResumeExperience(org=org, role=role, bullets=list(bullets), **kw)


def inputs(role: str = "sde-backend", **kw) -> ScoringInputs:
    kw.setdefault("resume", ResumeProfile())
    return ScoringInputs(today=TODAY, target_role_id=role, **kw)


def steady_weeks(count: int = 5, n: int = 26) -> list[WeekCount]:
    start = TODAY - timedelta(days=7 * n)
    return [WeekCount(week_start=start + timedelta(days=7 * i), count=count) for i in range(n)]


def rich_inputs(**overrides) -> ScoringInputs:
    """A realistic student: resume, GitHub, LinkedIn, two repos (one flagged) and a design item."""
    r = resume(
        skills=[
            "Python",
            "FastAPI",
            "SQL",
            "Docker",
            "pytest",
            "React",
            "Kubernetes",
            "AWS",
            "Communication",
        ],
        education=[ResumeEducation(institution="Example Institute of Technology")],
        experience=[
            experience(
                "Reduced API response time by 35% by adding Redis caching to two endpoints",
                "Documented the deployment steps for new interns",
            )
        ],
        projects=[
            ResumeProject(
                title="campus-api",
                description="REST API for campus events built with FastAPI and PostgreSQL. Handled 10,000 requests.",
                mentioned_technologies=["FastAPI", "PostgreSQL"],
            )
        ],
        certifications=[ResumeCertification(name="Intro to SQL", issuer="Kaggle")],
        page_count_hint=1,
    )
    campus = code_project(
        "campus-api",
        skills=["python", "fastapi", "sql", "docker", "rest-api", "pytest"],
        languages=["python"],
        signals=sig(
            **{**PERFECT, "has_ci": False, "has_demo_url": False, "authored_commits": 34, "total_commits": 36}
        ),
    )
    weather = code_project(
        "weather-dashboard",
        skills=["javascript"],
        signals=sig(authored_commits=14, total_commits=14, readme_is_template=True),
        flags=[flag("default_readme")],
    )
    base = {
        "resume": r,
        "has_linkedin": True,
        "linkedin_skill_ids": ["git"],
        "github_linked": True,
        "weeks": steady_weeks(3),
        "last_active_date": TODAY - timedelta(days=3),
        "projects": [campus, weather, design_project()],
    }
    return inputs(**{**base, **overrides})
