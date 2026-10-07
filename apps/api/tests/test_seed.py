from datetime import date

from sqlalchemy import func, select

from app.db import models
from app.db.base import SessionLocal
from app.schemas.api import AnalysisReport
from app.services import cohorts
from scripts.seed_demo import BANDS, COHORT_NAME, seed

TODAY = date(2026, 10, 7)


def _seed() -> dict:
    with SessionLocal() as db:
        return seed(db, TODAY).__dict__


def _scores(db) -> dict[str, float]:
    return {
        p.name: p.latest_score
        for p in db.scalars(select(models.Profile).where(models.Profile.cohort_id.is_not(None)))
    }


def test_seed_makes_forty_students_in_the_wanted_bands(client):
    summary = _seed()
    assert summary["students"] == 40 and summary["bands"] == BANDS
    with SessionLocal() as db:
        cohort = db.scalar(select(models.Cohort).where(models.Cohort.name == COHORT_NAME))
        profiles = list(cohort.profiles)
        assert len(profiles) == 40 and len({p.name for p in profiles}) == 40
        bands = {"not_ready": 0, "developing": 0, "ready": 0}
        for p in profiles:
            analysis = db.get(models.Analysis, p.latest_analysis_id)
            assert analysis.status == "done" and analysis.signals
            bands[AnalysisReport.model_validate(analysis.report).score.band.value] += 1
        assert bands == BANDS
        assert {d: sum(1 for p in profiles if p.department == d) for d in ("CSE", "IT", "ECE")} == {
            "CSE": 24, "IT": 10, "ECE": 6,
        }  # fmt: skip


def test_seed_is_repeatable_and_does_not_duplicate(client):
    _seed()
    with SessionLocal() as db:
        first = _scores(db)
    _seed()
    with SessionLocal() as db:
        assert _scores(db) == first
        assert db.scalar(select(func.count()).select_from(models.Cohort)) == 1
        assert (
            db.scalar(select(func.count()).select_from(models.Profile)) == 41
        )  # 40 students + the demo profile
        assert db.scalar(select(func.count()).select_from(models.Analysis)) == 41


def test_seed_leaves_other_data_alone(client):
    with SessionLocal() as db:
        other = models.Cohort(name="Other cohort")
        db.add(other)
        db.flush()
        db.add(models.Profile(name="Someone Real", cohort_id=other.id))
        db.commit()
    _seed()
    with SessionLocal() as db:
        assert db.scalar(select(models.Profile).where(models.Profile.name == "Someone Real")) is not None
        assert db.scalar(select(models.Cohort).where(models.Cohort.name == "Other cohort")) is not None


def test_seed_shows_the_kubernetes_pattern(client):
    summary = _seed()
    with SessionLocal() as db:
        rows, profiles = cohorts.load_rows(db, summary["cohort_id"], "sde-backend")
        insights = cohorts.aggregate(rows, profiles, summary["cohort_id"], "sde-backend")
    rates = {r.skill_id: r for r in insights.unverified_rate_by_skill}
    assert rates["kubernetes"].claimed_by >= 15
    assert rates["kubernetes"].unverified_rate > rates["docker"].unverified_rate
    assert rates["kubernetes"].unverified_rate >= 80
    assert insights.at_risk_count > 0 and insights.analysed_count == 40


def test_seed_invents_no_accounts_or_links(client):
    _seed()
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(models.Profile)
                .where(models.Profile.github_username.is_not(None))
            )
            == 0
        )
        for analysis in db.scalars(select(models.Analysis)):
            report = AnalysisReport.model_validate(analysis.report)
            assert all(e.url is None for e in report.evidence)
            assert all(p.url is None and p.demo_url is None for p in report.projects)
            assert "Synthetic demo data." in report.notes


def test_seed_gives_the_demo_profile_an_analysis_once(client):
    summary = _seed()
    with SessionLocal() as db:
        demo = db.get(models.Profile, summary["demo_profile_id"])
        assert demo.auth_subject == "dev" and demo.cohort_id is None
        first = demo.latest_analysis_id
        assert first is not None and demo.latest_score is not None
    _seed()
    with SessionLocal() as db:
        assert db.get(models.Profile, summary["demo_profile_id"]).latest_analysis_id == first
