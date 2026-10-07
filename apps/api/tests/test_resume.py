from pathlib import Path

import pytest

from app.db import models
from app.db.base import SessionLocal
from app.errors import ApiError
from app.prompts import load_prompt
from app.schemas.llm import ResumeProfile
from app.services.ingest import extract_text
from app.services.resume import extract_resume

FIXTURES = Path(__file__).parent / "fixtures"
RECORDED = (FIXTURES / "llm" / "extract_resume.json").read_text(encoding="utf-8")


class RecordedProvider:
    name = "recorded"

    def __init__(self, reply: str = RECORDED):
        self.reply = reply
        self.calls: list[dict] = []

    def model_for(self, tier):
        return "recorded-model"

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        return self.reply


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def profile(db):
    doc = extract_text("resume.pdf", (FIXTURES / "resume.pdf").read_bytes())
    profile = models.Profile(
        name="Aarav Mehta",
        linkedin_text="Aarav Mehta. Backend intern at Northwind Labs. Reach me at aarav.mehta@example.com",
    )
    profile.documents.append(
        models.Document(kind="resume", filename="resume.pdf", text=doc.text, page_count=doc.page_count)
    )
    db.add(profile)
    db.commit()
    return profile


def test_prompt_template_matches_pipeline_md():
    prompt = load_prompt("extract_resume")
    assert prompt.system.startswith("You are a precise resume parser. Extract only what is written.")
    assert "{resume_text}" in prompt.user_template and "{linkedin_text}" in prompt.user_template
    assert prompt.user(resume_text="A {weird} resume", linkedin_text="").count("A {weird} resume") == 1
    with pytest.raises(KeyError):
        prompt.user(resume_text="only one value")


def test_nothing_personal_reaches_the_model(db, profile):
    provider = RecordedProvider()
    extract_resume(profile, db, providers=[provider])
    sent = provider.calls[0]["system"] + provider.calls[0]["user"]
    for secret in (
        "aarav",
        "mehta",
        "example.com",
        "98765",
        "careerlens-demo",
        "github.com",
        "linkedin.com/in",
    ):
        assert secret not in sent.lower(), secret
    # the content the model needs is still there
    assert "Reduced API response time by 35%" in sent and "Python, FastAPI, SQL" in sent
    assert "Backend intern at Northwind Labs" in sent  # pasted LinkedIn text, also stripped
    assert provider.calls[0]["schema"] is ResumeProfile and provider.calls[0]["timeout"] == 30.0


def test_result_is_restored_and_page_count_comes_from_the_file(db, profile):
    result = extract_resume(profile, db, providers=[RecordedProvider()])
    assert [p.links for p in result.projects] == [
        ["https://github.com/careerlens-demo/campus-api"],
        ["https://github.com/careerlens-demo/weather-dashboard"],
    ]
    assert result.skills[:3] == ["Python", "FastAPI", "SQL"]
    assert result.experience[0].org == "Northwind Labs" and len(result.experience[0].bullets) == 3
    assert result.page_count_hint == 2


def test_second_run_is_served_from_cache(db, profile):
    extract_resume(profile, db, providers=[RecordedProvider()])
    idle = RecordedProvider()
    again = extract_resume(profile, db, providers=[idle])
    assert idle.calls == [] and again.projects[0].title == "campus-api"
    # the cached object holds placeholders, not the student's real links
    cached = db.query(models.CacheEntry).one().value
    assert cached["projects"][0]["links"] == ["[URL_4]"]


def test_no_resume_is_a_409(db):
    profile = models.Profile(name="No Resume")
    db.add(profile)
    db.commit()
    with pytest.raises(ApiError) as exc:
        extract_resume(profile, db, providers=[RecordedProvider()])
    assert (exc.value.status_code, exc.value.code) == (409, "no_resume")


@pytest.mark.live
def test_live_extraction_on_the_fixture_resume(db, profile):
    """Real provider call. Run with: uv run pytest -m live -q"""
    from app.config import Settings
    from app.services.llm import build_providers

    providers = build_providers(Settings())  # reads apps/api/.env
    if not providers:
        pytest.skip("no LLM key configured in apps/api/.env")
    result = extract_resume(profile, db, providers=providers, force_refresh=True)
    assert {"python", "fastapi"} <= {s.lower() for s in result.skills}
    assert any("campus" in p.title.lower() for p in result.projects)
    assert result.experience and "northwind" in result.experience[0].org.lower()
