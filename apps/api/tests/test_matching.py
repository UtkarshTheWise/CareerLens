from app.db import models
from app.db.base import SessionLocal
from app.main import app
from app.routers.jobs import get_llm_providers
from app.schemas.api import EvidenceLevel, JobPosting
from app.services import matching, scoring
from app.services.llm import ProviderUnavailable
from tests.llm_fakes import SchemaProvider
from tests.scoring_helpers import code_project, rich_inputs
from tests.scoring_helpers import inputs as bare_inputs


def posting(required=(), nice=(), source="manual", description="Backend intern role.", **kw) -> JobPosting:
    return JobPosting(
        title="Backend Engineer Intern", description=description, required_skills=list(required),
        nice_to_have=list(nice), source=source, **kw,
    )  # fmt: skip


# ---------------------------------------------------------------- skill resolution


def test_resolve_skills_uses_aliases_phrases_and_reports_unknown():
    ids, unknown = matching.resolve_skills(
        ["ReactJS", "Docker and Kubernetes", "Python", "Python", "Synergy"]
    )
    assert ids == ["react", "docker", "kubernetes", "python"]
    assert unknown == ["Synergy"]


# ---------------------------------------------------------------- the maths


def test_match_credits_each_level():
    inputs = rich_inputs()
    levels = scoring.skill_levels(inputs, ["python", "docker", "kubernetes", "terraform"])
    assert levels["python"][0] == EvidenceLevel.strong
    assert levels["docker"][0] == EvidenceLevel.strong
    assert levels["kubernetes"] == (EvidenceLevel.unverified, True)
    assert levels["terraform"] == (EvidenceLevel.missing, False)

    result = matching.match(inputs, posting(["Python", "Docker", "Kubernetes", "Terraform"]))
    assert result.keyword_match == 75.0  # 3 of 4 on the profile
    assert result.evidence_match == 52.5  # (1 + 1 + 0.10 + 0) / 4
    assert [m.skill_id for m in result.matched] == ["python", "docker", "kubernetes"]
    assert result.unverified == ["Kubernetes"]
    assert result.missing == ["Terraform"]
    assert "3 of the 4 required skills" in result.summary
    assert "Kubernetes is claimed without evidence yet." in result.summary
    assert "Terraform is not on your profile." in result.summary
    assert result.normalized_posting.required_skills == ["Python", "Docker", "Kubernetes", "Terraform"]


def test_evidence_never_exceeds_keyword_match():
    result = matching.match(rich_inputs(), posting(["Python", "FastAPI", "SQL", "Kubernetes", "AWS", "Rust"]))
    assert 0 <= result.evidence_match <= result.keyword_match <= 100


def test_nice_to_have_is_the_denominator_when_nothing_is_required():
    result = matching.match(rich_inputs(), posting(nice=["Python", "Terraform"]))
    assert result.keyword_match == 50.0
    assert "preferred skill" in result.summary


def test_nice_to_have_does_not_repeat_required_skills():
    result = matching.match(rich_inputs(), posting(["Python"], nice=["Python", "Terraform"]))
    assert result.normalized_posting.required_skills == ["Python"]
    assert result.normalized_posting.nice_to_have == ["Terraform"]
    assert result.keyword_match == 100.0  # nice-to-have never changes the score


def test_unknown_skills_are_not_counted_but_named():
    result = matching.match(rich_inputs(), posting(["Python", "Synergy"]))
    assert result.keyword_match == 100.0
    assert "Synergy" in result.summary and "weren't counted" in result.summary
    assert result.normalized_posting.required_skills == ["Python", "Synergy"]


def test_no_recognisable_skills_gives_zero_and_says_so():
    result = matching.match(rich_inputs(), posting(["Synergy"]))
    assert (result.keyword_match, result.evidence_match) == (0, 0)
    assert result.matched == [] and result.missing == []
    assert "no recognisable skills" in result.summary


def test_empty_profile_matches_nothing():
    result = matching.match(bare_inputs(), posting(["Python", "Docker"]))
    assert (result.keyword_match, result.evidence_match) == (0, 0)
    assert result.missing == ["Python", "Docker"]


def test_skill_found_in_repos_but_not_on_resume_is_mentioned():
    inputs = bare_inputs(github_linked=True, projects=[code_project("shop-api", skills=["redis"])])
    assert scoring.skill_levels(inputs, ["redis"])["redis"] == (EvidenceLevel.strong, False)
    result = matching.match(inputs, posting(["Redis"]))
    assert result.keyword_match == 100.0
    assert "Redis appears in your repositories but not on your resume" in result.summary


# ---------------------------------------------------------------- extraction


def test_normalize_keeps_postings_that_already_list_skills(client):
    provider = SchemaProvider({})
    with SessionLocal() as db:
        out, notes = matching.normalize_posting(
            posting(["Python"], source="jsonld"), db, providers=[provider]
        )
    assert out.required_skills == ["Python"] and notes == [] and provider.calls == []


def test_normalize_extracts_when_the_page_listed_nothing(client):
    provider = SchemaProvider(
        {
            "JobPostingExtract": {
                "title": "Backend Engineer Intern", "company": "Northwind Labs", "location": "Chennai",
                "required_skills": ["Python", "FastAPI"], "nice_to_have": ["Redis"], "deadline": "2026-11-30",
            }
        }
    )  # fmt: skip
    description = "Contact jobs@northwind.example. We need Python and FastAPI."
    with SessionLocal() as db:
        out, _ = matching.normalize_posting(posting(description=description), db, providers=[provider])
    assert out.required_skills == ["Python", "FastAPI"] and out.nice_to_have == ["Redis"]
    assert out.company == "Northwind Labs" and str(out.deadline) == "2026-11-30"
    assert "jobs@northwind.example" not in provider.prompts  # PII stripped before the call


def test_normalize_keeps_what_the_page_gave_over_the_extractor(client):
    provider = SchemaProvider(
        {"JobPostingExtract": {"title": "x", "company": "Other", "required_skills": ["SQL"]}}
    )
    with SessionLocal() as db:
        out, _ = matching.normalize_posting(posting(source="llm", company="Mine"), db, providers=[provider])
    assert out.company == "Mine"


def test_normalize_falls_back_to_scanning_when_the_llm_is_down(client):
    provider = SchemaProvider({"JobPostingExtract": ProviderUnavailable("down")})
    with SessionLocal() as db:
        out, notes = matching.normalize_posting(
            posting(description="You will build REST APIs with Python and Docker."), db, providers=[provider]
        )
    assert {"Python", "Docker"} <= set(out.required_skills)
    assert notes and "scanning" in notes[0]


# ---------------------------------------------------------------- route


def _profile(with_analysis: str | None = "done") -> str:
    """A profile; with an analysis of the given status unless `with_analysis` is None."""
    inputs = rich_inputs()
    with SessionLocal() as db:
        profile = models.Profile(name="Match Student", target_role_id="sde-backend")
        db.add(profile)
        db.flush()
        if with_analysis:
            db.add(
                models.Analysis(
                    profile_id=profile.id, role_id="sde-backend", status=with_analysis, progress=100,
                    signals=inputs.model_dump(mode="json"),
                )
            )  # fmt: skip
        db.commit()
        return profile.id


def _body(profile_id: str, **kw) -> dict:
    p = posting(["Python", "Docker", "Kubernetes", "Terraform"], **kw)
    return {"profile_id": profile_id, "posting": p.model_dump(mode="json")}


def test_match_route_returns_the_contract_shape(client):
    res = client.post("/v1/jobs/match", json=_body(_profile()))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["keyword_match"] == 75.0 and body["evidence_match"] == 52.5
    assert body["matched"][0] == {"skill_id": "python", "skill_name": "Python", "level": "strong"}
    assert body["normalized_posting"]["source"] == "manual"


def test_match_route_uses_the_llm_for_llm_sourced_postings(client):
    provider = SchemaProvider(
        {"JobPostingExtract": {"title": "x", "required_skills": ["Python", "Terraform"]}}
    )
    app.dependency_overrides[get_llm_providers] = lambda: [provider]
    body = {"profile_id": _profile(), "posting": posting(source="llm").model_dump(mode="json")}
    res = client.post("/v1/jobs/match", json=body)
    assert res.status_code == 200 and res.json()["keyword_match"] == 50.0


def test_match_route_needs_a_finished_analysis(client):
    for pid in (_profile(None), _profile("extracting")):
        res = client.post("/v1/jobs/match", json=_body(pid))
        assert res.status_code == 409 and res.json()["code"] == "no_analysis"


def test_match_route_unknown_profile_is_404(client):
    res = client.post("/v1/jobs/match", json=_body("00000000-0000-4000-8000-000000000000"))
    assert res.status_code == 404
