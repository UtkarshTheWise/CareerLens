"""The collector and detectors end to end on a recorded real profile (no network)."""

import json
import re
from datetime import UTC, datetime, timedelta

import pytest

from app.config import Settings
from app.db.base import SessionLocal
from app.db.models import CacheEntry
from app.services.detectors import analyse
from app.services.github import GitHubClient, collect
from scripts.github_fixtures import FIXTURE_ROOT, ReplayTransport

LOGIN = "UtkarshTheWise"
BANNED = ("slop", "fake", "larp", "dishonest", "cheat", "copied", "plagiar", "ai-generated")


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def transport():
    return ReplayTransport(FIXTURE_ROOT / LOGIN)


@pytest.fixture
def client(db, transport):
    return GitHubClient(db, Settings(_env_file=None, github_token="not-a-real-token"), transport=transport)


@pytest.fixture
def snapshot(db, client):
    return collect(LOGIN, db, client=client)


TOKEN_SHAPES = re.compile(r"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}")


def test_fixture_holds_no_credentials():
    """README text may mention 'Bearer' (it is documentation); an actual token or header may not appear."""
    files = list((FIXTURE_ROOT / LOGIN).glob("*.json"))
    assert len(files) >= 10
    for file in files:
        raw = file.read_text(encoding="utf-8")
        assert not TOKEN_SHAPES.search(raw), file.name
        assert set(json.loads(raw)) == {"method", "url", "request", "status", "body"}  # never request headers


def test_profile_and_repo_selection(snapshot):
    assert snapshot.login == LOGIN and snapshot.user_id
    assert len(snapshot.repos) == 14
    forks = [r for r in snapshot.repos if r.is_fork]
    assert [r.name for r in forks] == ["neohomes", "amity", "ordin20"]

    detailed = snapshot.detailed_repos
    assert len(detailed) == 8 and not any(r.is_fork for r in detailed)
    assert [r.name for r in detailed][:3] == [
        "CareerLens",
        "patm",
        "SimpleHabitTracker",
    ]  # most recently pushed first
    pushed = [r.pushed_at for r in snapshot.repos]
    assert pushed == sorted(pushed, reverse=True)

    assert all(r.tree and r.has_commit_facts for r in detailed)
    assert all(r.has_commit_facts and not r.tree and not r.detailed for r in forks)  # facts only, no tree
    assert not any(r.tree_truncated for r in detailed)


def test_commit_facts(snapshot):
    by_name = {r.name: r for r in snapshot.repos}
    gdg = by_name["GDG_Round2"]
    assert (gdg.total_commits, gdg.authored_commits, gdg.first_commit_share) == (1, 1, 1.0)
    assert (
        by_name["timetableanalyzer"].total_commits == 30
        and by_name["timetableanalyzer"].active_span_weeks > 40
    )
    assert by_name["neohomes"].authored_since_created > 0  # a fork with own commits
    assert by_name["amity"].authored_since_created == 0 and by_name["amity"].total_commits == 27
    assert by_name["ordin20"].first_commit_share is None  # more than 100 commits: share is not computable


def test_contribution_calendar_is_26_weeks_oldest_first(snapshot):
    assert len(snapshot.weeks) == 26
    starts = [w.week_start for w in snapshot.weeks]
    assert starts == sorted(starts) and all(
        (b - a).days == 7 for a, b in zip(starts, starts[1:], strict=False)
    )
    assert all(w.count >= 0 for w in snapshot.weeks)
    assert snapshot.last_active_date is not None and snapshot.total_contributions >= 0


def test_second_collect_makes_no_http_calls_and_entries_expire_in_24h(db, client, transport):
    first = collect(LOGIN, db, client=client)
    made = transport.requests
    assert made == 11  # overview + 8 trees + commit facts for the repos and for the forks
    again = collect(LOGIN, db, client=client)
    assert transport.requests == made
    assert again.model_dump() == first.model_dump()

    entries = db.query(CacheEntry).all()
    assert len(entries) == made and {e.kind for e in entries} == {"github"}
    assert all(timedelta(hours=23) < e.expires_at - datetime.now(UTC) <= timedelta(hours=24) for e in entries)


def test_detectors_on_the_real_repos(snapshot):
    result = analyse(snapshot)
    assert set(result) == {r.name for r in snapshot.repos if r.detailed or r.has_commit_facts}
    assert len(result) == 11

    def flags(name):
        return {f.code for f in result[name].flags}

    assert "single_dump" in flags("GDG_Round2") and "single_dump" in flags(
        "CareerLens"
    )  # 1 and 3 authored commits
    assert "single_dump" in flags("patm")  # 4 commits, first one adds 91 % of the lines
    assert flags("amity") == {"unmodified_fork"} and flags("ordin20") == {"unmodified_fork"}
    assert flags("neohomes") == set()  # a fork the student did commit to
    assert flags("timetableanalyzer") == set() and flags("Swolo") == set()

    assert "python" in result["SABTA"].skills and "python" in result["SABTA"].language_skills
    assert "react" in result["SimpleHabitTracker"].skills  # from package.json
    assert {"javascript", "html-css"} <= set(result["Swolo"].skills)
    assert "rest-api" in result["CareerLens"].skills  # openapi.yaml
    for analysis in result.values():
        assert analysis.signals.authored_commits <= analysis.signals.total_commits
        for hit_list in analysis.skills.values():
            assert all(h.detail for h in hit_list)


def test_analysis_is_deterministic_and_wording_is_neutral(snapshot, transport):
    first = {n: a.model_dump() for n, a in analyse(snapshot).items()}
    second = {n: a.model_dump() for n, a in analyse(snapshot).items()}
    assert first == second
    for analysis in analyse(snapshot).values():
        for flag in analysis.flags:
            assert not any(word in f"{flag.reason} {flag.fix}".lower() for word in BANNED)


def test_file_fetches_are_cached_too(db, client, transport, snapshot):
    analyse(snapshot)
    after_first = transport.requests
    analyse(snapshot)
    assert transport.requests == after_first
