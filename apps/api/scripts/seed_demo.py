"""Seed the demo cohort: 40 synthetic students whose analyses come from the real scoring engine.

    uv run python scripts/seed_demo.py [--today 2026-10-07]

Writes to DATABASE_URL (SQLite locally, Supabase in deploy). No LLM, GitHub or network call: for each
student a synthetic set of derived facts (`ScoringInputs`) is generated and `scoring.score` turns it into
a stored `AnalysisReport`, exactly as a real analysis would, so the cohort dashboard shows what real data
would. Re-running replaces the previous seed (the cohort and its students) and leaves other data alone.

Everything here is invented: made-up names, no GitHub usernames, no repository URLs. The mix is ~30 % not
ready, ~45 % developing, ~25 % ready, with one visible pattern: most students list Docker and Kubernetes
and almost none can show Kubernetes in a repository.
"""

import argparse
import logging
import random
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app import catalogue  # noqa: E402
from app.db import models  # noqa: E402
from app.db.base import SessionLocal, create_all  # noqa: E402
from app.deps import demo_profile  # noqa: E402
from app.schemas.api import AnalysisReport  # noqa: E402
from app.schemas.llm import (  # noqa: E402
    ResumeCertification,
    ResumeEducation,
    ResumeExperience,
    ResumeProfile,
    ResumeProject,
)
from app.services import scoring  # noqa: E402
from app.services.detectors import FLAG_SEVERITY, DetectorHit, RepoSignals  # noqa: E402
from app.services.github import WeekCount  # noqa: E402
from app.services.pipeline import save_report  # noqa: E402
from app.services.planner import plan_roadmap  # noqa: E402
from app.services.scoring_inputs import FlagInput, ProjectInput, ScoringInputs  # noqa: E402

COHORT_NAME = "B.Tech CSE 2027"
SEED = 2027
BANDS = {"not_ready": 12, "developing": 18, "ready": 10}  # of 40: 30 % / 45 % / 25 %
DEPARTMENTS = {"CSE": 24, "IT": 10, "ECE": 6}
ROLES = {"sde-backend": 28, "full-stack": 7, "data-analyst": 5}
# Where the latent skill level t is drawn from, per target band; the score decides the final band.
T_RANGE = {"not_ready": (0.02, 0.5), "developing": (0.35, 0.8), "ready": (0.7, 1.0)}
MAX_DRAWS = 400

FIRST = [
    "Aarav", "Diya", "Kabir", "Meera", "Rohan", "Ananya", "Vihaan", "Ishita", "Arjun", "Saanvi", "Reyansh",
    "Kavya", "Aditya", "Nisha", "Dev", "Pooja", "Karthik", "Tanvi", "Siddharth", "Riya", "Manav", "Neha",
    "Yash", "Sneha", "Harsh", "Divya", "Pranav", "Anika", "Varun", "Lakshmi", "Tejas", "Shreya", "Nikhil",
    "Aditi", "Rahul", "Mira", "Omkar", "Bhavna", "Samar", "Tara",
]  # fmt: skip
LAST = [
    "Sharma", "Iyer", "Reddy", "Nair", "Gupta", "Menon", "Patel", "Rao", "Singh", "Das", "Kulkarni", "Joshi",
    "Bose", "Pillai", "Verma", "Chopra", "Bhat", "Naidu", "Mehta", "Kapoor",
]  # fmt: skip
PROJECT_NAMES = [
    "campus-api", "task-tracker", "expense-app", "chat-server", "library-system", "weather-board",
    "quiz-platform", "notes-sync", "event-planner", "inventory-api", "job-board", "recipe-finder",
    "habit-tracker", "ticket-desk", "study-planner", "bus-routes",
]  # fmt: skip
COMPANIES = ["Northwind Labs", "Contoso Systems", "Fabrikam Tech", "Tailspin Software", "Adatum Cloud"]
BACKEND_ROLES = {"sde-backend", "full-stack"}


@dataclass
class Summary:
    cohort_id: str
    students: int
    bands: dict[str, int]
    demo_profile_id: str


def _pick(rng: random.Random, p: float) -> bool:
    return rng.random() < p


def _spread(rng: random.Random, quotas: dict[str, int]) -> list[str]:
    """Each quota key repeated by its count, in a seeded random order."""
    items = [k for k, n in quotas.items() for _ in range(n)]
    rng.shuffle(items)
    return items


# ---------------------------------------------------------------- one synthetic student


def _signals(rng: random.Random, t: float) -> RepoSignals:
    authored = rng.randint(3, 8) + int(t * rng.randint(10, 45))
    share = rng.uniform(0.55, 1.0) if t > 0.3 else rng.uniform(0.3, 1.0)
    total = max(authored, round(authored / share))
    substantive = _pick(rng, 0.3 + 0.6 * t)
    return RepoSignals(
        readme_chars=900 if substantive else 120,
        readme_is_template=not substantive and _pick(rng, 0.4),
        readme_substantive=substantive,
        readme_has_setup_or_screenshots=_pick(rng, 0.2 + 0.6 * t),
        has_description=_pick(rng, 0.5 + 0.4 * t),
        has_license=_pick(rng, 0.15 + 0.4 * t),
        has_demo_url=_pick(rng, 0.1 + 0.4 * t),
        has_tests=_pick(rng, 0.1 + 0.7 * t),
        has_ci=_pick(rng, 0.05 + 0.5 * t),
        has_manifest=True,
        has_lockfile=_pick(rng, 0.3 + 0.4 * t),
        module_count=rng.randint(1, 2 + int(3 * t)),
        has_deploy_config=_pick(rng, 0.1 + 0.4 * t),
        commit_facts_known=True,
        authored_commits=authored,
        total_commits=total,
        authored_share=round(authored / total, 2),
        active_span_weeks=round(rng.uniform(0.5, 2 + 10 * t), 1),
        code_kb=round(rng.uniform(3, 15 + 60 * t), 1),
    )


def _flags(signals: RepoSignals) -> list[FlagInput]:
    flags = []
    if not signals.readme_substantive and signals.readme_is_template:
        code = "default_readme"
        flags.append(
            FlagInput(
                code=code,
                severity=FLAG_SEVERITY[code],
                reason="The README is still the starter template",
                fix="Replace it with what the project does, how to run it and a screenshot",
            )
        )
    if signals.active_span_weeks < 1 and signals.total_commits > 3:
        code = "single_dump"
        flags.append(
            FlagInput(
                code=code,
                severity=FLAG_SEVERITY[code],
                reason="Most of the history was added in a single sitting",
                fix="Commit in small steps as you build, so the history shows how the project grew",
            )
        )
    return flags


def _weeks(rng: random.Random, t: float, today: date) -> tuple[list[WeekCount], date | None]:
    start = today - timedelta(days=7 * 26)
    active_p = 0.15 + 0.75 * t
    weeks = []
    for i in range(26):
        count = rng.randint(1, 3 + int(8 * t)) if _pick(rng, active_p) else 0
        weeks.append(WeekCount(week_start=start + timedelta(days=7 * i), count=count))
    active = [w for w in weeks if w.count]
    last = active[-1].week_start + timedelta(days=rng.randint(0, 6)) if active else None
    return weeks, min(last, today) if last else None


def generate_inputs(
    rng: random.Random, role_id: str, t: float, today: date, department: str
) -> ScoringInputs:
    """Derived facts for one student whose skill level is `t` (0 = beginner, 1 = very strong)."""
    role = catalogue.get_role(role_id)
    pool = [rs.skill_id for rs in role.skills]
    footprint = [s for s in pool if not catalogue.get_skill(s).detectors.is_empty]
    backend = role_id in BACKEND_ROLES

    github = _pick(rng, 0.45 + 0.5 * t)
    evidenced: set[str] = set()
    if github:
        for skill in footprint:
            if skill == "kubernetes":
                if _pick(rng, 0.04):
                    evidenced.add(skill)
            elif skill == "docker":
                if _pick(rng, 0.15 + 0.35 * t):
                    evidenced.add(skill)
            elif _pick(rng, max(0.0, 1.05 * t - 0.1)):
                evidenced.add(skill)

    claimed = {s for s in evidenced if _pick(rng, 0.85)}
    claimed |= {s for s in pool if s not in evidenced and _pick(rng, 0.25 + 0.2 * (1 - t))}
    if backend and _pick(rng, 0.6):  # the cohort-wide pattern: claimed in the skills list, rarely shown
        claimed |= {"docker", "kubernetes"}

    projects, resume_projects = [], []
    if github:
        names = rng.sample(PROJECT_NAMES, rng.randint(1, 2 + int(2 * t)))
        skills_left = sorted(evidenced)
        rng.shuffle(skills_left)
        for n, title in enumerate(names):
            share = skills_left[n :: len(names)]
            signals = _signals(rng, t)
            project = ProjectInput(
                project_id=scoring.project_id_for(title),
                title=title,
                signals=signals,
                skills={s: [DetectorHit(kind="pip", detail=s)] for s in share},
                language_skills=[s for s in share if s in ("python", "javascript", "java")][:1],
                claimed_skill_ids=share,
                flags=_flags(signals),
            )
            projects.append(project)
            tech = [catalogue.get_skill(s).name for s in share]
            metric = (
                f" Handles {rng.choice([200, 500, 2000])} requests in load tests." if _pick(rng, t) else ""
            )
            resume_projects.append(
                ResumeProject(
                    title=title,
                    description=f"A {title.replace('-', ' ')} built with {', '.join(tech) or 'Python'}."
                    + metric,
                    mentioned_technologies=tech,
                )
            )

    experience = []
    if _pick(rng, 0.1 + 0.6 * t):
        bullet = "Shipped endpoints used by the support team"
        bullets = [bullet + (f", cutting handling time by {rng.randint(15, 60)}%" if _pick(rng, 0.5) else "")]
        experience.append(
            ResumeExperience(
                org=rng.choice(COMPANIES),
                role="Software Intern",
                bullets=bullets,
                start="2026-05",
                end="2026-07",
            )
        )

    weeks, last_active = _weeks(rng, t, today) if github else ([], None)
    linkedin = _pick(rng, 0.35 + 0.5 * t)
    names = sorted(catalogue.get_skill(s).name for s in claimed)
    resume = ResumeProfile(
        headline="B.Tech student",
        education=[
            ResumeEducation(
                institution="Example Institute of Technology", degree="B.Tech", field=department, end="2027"
            )
        ],
        skills=names,
        experience=experience,
        projects=resume_projects,
        certifications=[ResumeCertification(name="Intro to SQL", issuer="Kaggle")] if _pick(rng, 0.3) else [],
        page_count_hint=1,
    )
    return ScoringInputs(
        today=today,
        target_role_id=role_id,
        resume=resume,
        has_contact=True,
        has_linkedin=linkedin,
        linkedin_skill_ids=sorted(rng.sample(sorted(claimed), min(len(claimed), 3))) if linkedin else [],
        github_linked=github,
        weeks=weeks,
        last_active_date=last_active,
        projects=projects,
    )


def draw_student(
    rng: random.Random, role_id: str, band: str, today: date, department: str
) -> tuple[ScoringInputs, float]:
    """Draw synthetic students until one scores into the wanted band (bounded, seeded: deterministic)."""
    lo, hi = T_RANGE[band]
    best: tuple[ScoringInputs, float] | None = None
    for _ in range(MAX_DRAWS):
        inputs = generate_inputs(rng, role_id, rng.uniform(lo, hi), today, department)
        total = scoring.score(inputs).breakdown.total
        if scoring._band(total).value == band:
            return inputs, total
        best = (inputs, total)
    raise RuntimeError(f"could not generate a '{band}' student for {role_id}; last score {best[1]}")


# ---------------------------------------------------------------- storing


def build_report(inputs: ScoringInputs, db: Session) -> AnalysisReport:
    """The report a real analysis would store, with the planner's deterministic fallback roadmap."""
    result = scoring.score(inputs)
    role = catalogue.get_role(inputs.target_role_id)
    roadmap, notes = plan_roadmap(inputs, result, role, db, providers=[])  # no LLM: fallback plan only
    return AnalysisReport(
        score=result.breakdown,
        coverage=result.coverage,
        claims=result.claims,
        gaps=result.gaps,
        projects=result.projects,
        role_fits=scoring.role_fits(inputs),
        roadmap=roadmap,
        consistency=result.consistency,
        evidence=result.evidence,
        notes=["Synthetic demo data.", *result.notes],
    )


def store_analysis(db: Session, profile: models.Profile, inputs: ScoringInputs) -> models.Analysis:
    analysis = models.Analysis(
        profile_id=profile.id, role_id=inputs.target_role_id, status="done", progress=100
    )
    db.add(analysis)
    db.flush()
    analysis.profile = profile
    save_report(analysis, inputs, build_report(inputs, db))
    return analysis


def remove_previous_seed(db: Session) -> None:
    for cohort in db.scalars(select(models.Cohort).where(models.Cohort.name == COHORT_NAME)):
        for profile in list(cohort.profiles):
            db.delete(profile)  # cascades to its documents, analyses and applications
        db.delete(cohort)
    db.flush()


def seed(db: Session, today: date) -> Summary:
    rng = random.Random(SEED)
    remove_previous_seed(db)
    cohort = models.Cohort(name=COHORT_NAME, department="CSE", year=2027)
    db.add(cohort)
    db.flush()

    bands, departments, roles = _spread(rng, BANDS), _spread(rng, DEPARTMENTS), _spread(rng, ROLES)
    names: set[str] = set()
    counts = {b: 0 for b in BANDS}
    for band, department, role_id in zip(bands, departments, roles, strict=True):
        name = next(
            n for n in iter(lambda: f"{rng.choice(FIRST)} {rng.choice(LAST)}", None) if n not in names
        )
        names.add(name)
        inputs, _ = draw_student(rng, role_id, band, today, department)
        profile = models.Profile(
            name=name, department=department, cohort_id=cohort.id, target_role_id=role_id, portfolio_urls=[]
        )
        db.add(profile)
        db.flush()
        store_analysis(db, profile, inputs)
        counts[band] += 1

    demo = demo_profile(db)
    if latest_done(db, demo) is None:
        inputs = generate_inputs(random.Random(SEED + 1), "sde-backend", 0.62, today, "CSE")
        demo.target_role_id = "sde-backend"
        store_analysis(db, demo, inputs)
    db.commit()
    return Summary(cohort.id, len(bands), counts, demo.id)


def latest_done(db: Session, profile: models.Profile) -> models.Analysis | None:
    return db.scalar(
        select(models.Analysis)
        .where(models.Analysis.profile_id == profile.id, models.Analysis.status == "done")
        .limit(1)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--today", type=date.fromisoformat, default=datetime.now(UTC).date())
    args = parser.parse_args(argv)
    logging.getLogger("careerlens").setLevel(logging.ERROR)  # the planner logs a warning per student
    create_all()
    with SessionLocal() as db:
        summary = seed(db, args.today)
    print(f"Seeded cohort '{COHORT_NAME}' ({summary.cohort_id}): {summary.students} students")
    print("Bands:", ", ".join(f"{k} {v}" for k, v in summary.bands.items()))
    print(f"Demo profile {summary.demo_profile_id} has an analysis for /v1/me and the extension")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
