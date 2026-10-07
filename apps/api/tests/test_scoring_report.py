"""Claims, gaps, project audits, role fit, evidence, reasons and the what-if simulator."""

import pytest

from app import catalogue
from app.schemas.api import (
    EvidenceLevel,
    SimulationChange,
    SimulationRequest,
    SkillLevelChange,
    Understanding,
)
from app.services.scoring import (
    apply_changes,
    changes_gain,
    flag_gain,
    flag_id_for,
    role_fits,
    score,
    simulate,
    skill_gain,
)
from app.services.scoring_inputs import DesignInput, ScoringInputs, SimulationError
from tests.scoring_helpers import (
    PERFECT,
    code_project,
    design_project,
    flag,
    hit,
    inputs,
    resume,
    rich_inputs,
    sig,
)

BANNED = (
    "slop",
    "fake",
    "larp",
    "dishonest",
    "cheat",
    "plagiar",
    "ai-generated",
    "didn't build",
    "did not build",
)


def comp(result, key):
    return next(c for c in result.breakdown.components if c.key == key)


def audit(result, title):
    return next(p for p in result.projects if p.title == title)


def level(result, skill_id):
    return next(c.level.value for c in result.claims if c.skill_id == skill_id)


# ---------------------------------------------------------------- determinism and storage


def test_same_input_gives_identical_output():
    a, b = score(rich_inputs()), score(rich_inputs())
    assert a.model_dump() == b.model_dump()
    assert role_fits(rich_inputs()) == role_fits(rich_inputs())


def test_inputs_survive_json_storage():
    original = rich_inputs()
    restored = ScoringInputs.model_validate_json(original.model_dump_json())
    assert restored == original
    assert score(restored).model_dump() == score(original).model_dump()


def test_only_the_passed_date_matters_not_the_clock():
    base = rich_inputs()
    later = base.model_copy(update={"today": base.today.replace(year=2030)})
    assert comp(score(later), "consistency").score < comp(score(base), "consistency").score  # recency decays
    assert comp(score(later), "skill_evidence").score == comp(score(base), "skill_evidence").score


def test_unknown_role_is_rejected():
    with pytest.raises(ValueError, match="unknown role"):
        score(inputs(), role_id="astronaut")


# ---------------------------------------------------------------- reasons and evidence


def test_positive_deltas_sum_to_each_component_score_and_negatives_are_withheld_points():
    result = score(rich_inputs())
    for c in result.breakdown.components:
        assert c.score is not None
        gained = sum(r.delta for r in c.reasons if r.delta > 0)
        withheld = -sum(r.delta for r in c.reasons if r.delta < 0)
        assert gained == pytest.approx(c.score, abs=0.12), c.key
        assert 0 <= withheld <= 100 - c.score + 0.12, c.key  # entries for items that earned nothing at all


def test_every_evidence_id_resolves_and_evidence_is_deduplicated():
    result = score(rich_inputs())
    known = [e.id for e in result.evidence]
    assert len(known) == len(set(known))
    used = {i for c in result.claims for i in c.evidence_ids}
    used |= {i for comp_ in result.breakdown.components for r in comp_.reasons for i in r.evidence_ids}
    assert used and used <= set(known)
    kinds = {e.kind for e in result.evidence}
    assert {"repo", "experience", "resume_text", "linkedin", "portfolio_item"} <= kinds
    # a certificate is listed only when it is the best evidence for something (here the repo outranks it)
    assert "certificate" not in kinds


def test_certificate_evidence_appears_when_it_is_the_best_evidence():
    result = score(inputs(resume=resume(certifications=[{"name": "Intro to SQL", "issuer": "Kaggle"}])))
    cert = next(e for e in result.evidence if e.kind == "certificate")
    assert cert.label == "Intro to SQL" and cert.source == "resume"
    assert cert.id in next(c for c in result.claims if c.skill_id == "sql").evidence_ids


def test_detector_files_become_linked_evidence():
    p = code_project("campus-api", signals=sig(**PERFECT))
    p.skills["docker"] = [hit("file", "deploy/Dockerfile")]
    result = score(inputs(github_linked=True, projects=[p]))
    files = [e for e in result.evidence if e.kind == "file"]
    assert [e.url for e in files] == ["https://github.com/u/campus-api/blob/HEAD/deploy/Dockerfile"]
    docker = next(c for c in result.claims if c.skill_id == "docker")
    assert files[0].id in docker.evidence_ids and "file deploy/Dockerfile" in docker.reason


def test_generated_text_never_accuses_the_student():
    p = code_project(
        "tutorial", signals=sig(authored_commits=1, total_commits=1), flags=[flag("single_dump")]
    )
    p.understanding, p.covered_skill_ids = Understanding.not_demonstrated, ["python"]
    p.skills["python"] = [hit()]
    result = score(
        inputs(github_linked=True, projects=[p, design_project()], resume=resume(skills=["Python"]))
    )
    texts = [c.reason for c in result.claims] + result.notes
    texts += [r.text for c in result.breakdown.components for r in c.reasons]
    texts += [f"{f.reason} {f.fix}" for a in result.projects for f in a.flags]
    texts += [t for fit in role_fits(rich_inputs()) for t in fit.reasons]
    assert texts and not any(word in t.lower() for t in texts for word in BANNED)


# ---------------------------------------------------------------- claims


def test_claims_cover_claimed_and_required_skills_strongest_first():
    result = score(rich_inputs())
    ids = {c.skill_id for c in result.claims}
    required = {rs.skill_id for rs in catalogue.get_role("sde-backend").skills}
    assert required <= ids  # unclaimed requirements show up as missing
    ranks = [
        ["missing", "unverified", "weak", "moderate", "strong"].index(c.level.value) for c in result.claims
    ]
    assert ranks == sorted(ranks, reverse=True)
    redis = next(c for c in result.claims if c.skill_id == "redis")
    assert redis.level == EvidenceLevel.moderate and redis.claimed  # quantified experience bullet
    assert next(c for c in result.claims if c.skill_id == "linux").claimed is False
    assert "Communication" not in {c.skill_name for c in result.claims}


# ---------------------------------------------------------------- gaps


def test_gaps_are_required_skills_below_moderate_ordered_by_gain():
    result = score(rich_inputs())
    required = {rs.skill_id for rs in catalogue.get_role("sde-backend").skills}
    below = {s for s in required if level(result, s) in ("weak", "unverified", "missing")}
    assert {g.skill_id for g in result.gaps} == below and below
    assert all(g.gap_id == f"gap-{g.skill_id}" for g in result.gaps)
    assert all(g.level.value in ("weak", "unverified", "missing") for g in result.gaps)
    key = [(-g.estimated_gain, -g.importance, g.skill_name) for g in result.gaps]
    assert key == sorted(key)
    by_id = {g.skill_id: g for g in result.gaps}
    assert by_id["kubernetes"].claimed is True and by_id["linux"].claimed is False


def test_gap_gain_is_the_recomputed_score_change():
    base = rich_inputs()
    result = score(base)
    assert any(g.estimated_gain > 0 for g in result.gaps)
    for gap in result.gaps[:4]:
        lifted = base.model_copy(update={"skill_overrides": {gap.skill_id: "strong"}})
        expected = round(score(lifted).breakdown.total - result.breakdown.total, 1)
        assert gap.estimated_gain == pytest.approx(max(0.0, expected))
        assert skill_gain(base, gap.skill_id) == gap.estimated_gain


# ---------------------------------------------------------------- project audits


def test_project_audits_carry_scores_flags_and_signals():
    result = score(rich_inputs())
    weather = audit(result, "weather-dashboard")
    assert weather.kind == "code" and weather.counted_in_score is True and weather.self_reported is False
    assert [f.code for f in weather.flags] == ["default_readme"]
    assert weather.flags[0].flag_id == "flag-weather-dashboard-default-readme"
    assert weather.flags[0].estimated_gain == flag_gain(
        rich_inputs(), "proj-weather-dashboard", "default_readme"
    )
    assert weather.flags[0].estimated_gain > 0
    assert weather.signals.authored_commits == 14 and weather.detected_skills == ["javascript"]

    campus = audit(result, "campus-api")
    assert campus.signals.tests is True and campus.signals.ci is False and campus.flags == []
    assert {"python", "fastapi", "sql", "docker"} <= set(campus.detected_skills)

    design = audit(result, "Transit app case study")
    assert design.kind == "design" and design.self_reported and design.subscores is None


def test_understanding_gap_flag_uses_quiz_text_when_given_and_resolves_via_the_quiz():
    p = code_project(
        skills=["python"], understanding=Understanding.not_demonstrated, covered_skill_ids=["python"]
    )
    default = audit(score(inputs(github_linked=True, projects=[p])), "campus-api").flags[0]
    assert default.code == "understanding_gap" and default.flag_id == "flag-campus-api-understanding-gap"
    custom = flag("understanding_gap").model_copy(update={"reason": "Your answers didn't yet cover db.py."})
    p.gap_flag = custom
    shown = audit(score(inputs(github_linked=True, projects=[p])), "campus-api").flags[0]
    assert shown.reason == "Your answers didn't yet cover db.py."
    assert shown.estimated_gain == flag_gain(
        inputs(github_linked=True, projects=[p]), p.project_id, "understanding_gap"
    )


# ---------------------------------------------------------------- role fit


def test_role_fit_is_the_total_recomputed_for_each_role_top_three():
    base = rich_inputs()
    fits = role_fits(base)
    assert len(fits) == 3 and len({f.role_id for f in fits}) == 3
    assert [f.score for f in fits] == sorted((f.score for f in fits), reverse=True)
    for fit in fits:
        assert fit.score == score(base, role_id=fit.role_id).breakdown.total
        assert fit.reasons and len(fit.top_missing) <= 3
    backend = next(f for f in role_fits(base) if f.role_id == "sde-backend")
    assert all(isinstance(name, str) for name in backend.top_missing)
    assert fits[0].role_id in {"sde-backend", "full-stack", "devops-cloud"}


def test_a_designer_profile_ranks_the_design_role_first():
    tools = ["Figma", "Wireframes", "Prototypes", "User research", "Visual design"]
    item = design_project(
        design=DesignInput(
            problem_statement=20,
            process_evidence=25,
            outcome_or_metrics=10,
            tool_evidence=12,
            presentation=8,
            tools_seen=tools,
        )
    )
    r = resume(skills=["Figma", "Wireframing", "Prototyping", "User research", "Visual design"])
    fits = role_fits(inputs(role="ui-ux-designer", resume=r, projects=[item]))
    assert fits[0].role_id == "ui-ux-designer"


# ---------------------------------------------------------------- what-if simulation


def one_repo(**signal_overrides):
    return inputs(
        github_linked=True, projects=[code_project(skills=["python"], signals=sig(**signal_overrides))]
    )


def project_score(base, changes):
    return audit(score(apply_changes(base, changes)), "campus-api").score


@pytest.mark.parametrize(
    ("signal", "points"),
    [("tests", 10), ("ci", 8), ("demo_url", 4), ("license", 3), ("readme", 10), ("deploy_config", 4)],
)
def test_each_signal_adds_its_scoring_md_points(signal, points):
    base = one_repo()
    before = audit(score(base), "campus-api").score
    after = project_score(base, [SimulationChange(project_id="proj-campus-api", add_signals=[signal])])
    assert after - before == pytest.approx(points)


def test_adding_tests_and_ci_raises_project_quality_and_the_total():
    base = one_repo()
    result = simulate(
        base,
        SimulationRequest(
            changes=[SimulationChange(project_id="proj-campus-api", add_signals=["tests", "ci"])]
        ),
    )
    before_b = next(c.score for c in result.before.components if c.key == "project_quality")
    after_b = next(c.score for c in result.after.components if c.key == "project_quality")
    assert after_b == pytest.approx(before_b + 18, abs=0.1)
    assert result.delta > 0 and result.delta == pytest.approx(
        result.after.total - result.before.total, abs=0.05
    )
    assert result.before == score(base).breakdown


def test_adding_ci_also_evidences_the_ci_cd_skill():
    base = one_repo()
    assert level(score(base), "ci-cd") == "missing"
    after = score(apply_changes(base, [SimulationChange(project_id="proj-campus-api", add_signals=["ci"])]))
    assert level(after, "ci-cd") == "strong"  # 20 of 20 commits are the student's


def test_simulation_never_changes_the_stored_inputs():
    base = one_repo()
    snapshot = base.model_dump()
    simulate(
        base,
        SimulationRequest(
            changes=[SimulationChange(project_id="proj-campus-api", add_signals=["tests", "ci", "readme"])]
        ),
    )
    assert base.model_dump() == snapshot


def test_a_null_project_id_applies_to_every_code_project():
    base = inputs(github_linked=True, projects=[code_project("one"), code_project("two"), design_project()])
    after = score(apply_changes(base, [SimulationChange(add_signals=["tests"])]))
    assert audit(after, "one").signals.tests and audit(after, "two").signals.tests


def test_resolving_a_flag_removes_it_and_restores_the_points():
    p = code_project(signals=sig(readme_is_template=True), flags=[flag("default_readme")])
    base = inputs(github_linked=True, projects=[p])
    fid = flag_id_for(p.project_id, "default_readme")
    after = score(apply_changes(base, [SimulationChange(resolve_flags=[fid])]))
    assert audit(after, "campus-api").flags == []
    assert (
        audit(after, "campus-api").subscores.authorship
        - audit(score(base), "campus-api").subscores.authorship
        == 5
    )


def test_resolving_understanding_gap_assumes_the_quiz_shows_understanding():
    p = code_project(
        skills=["python"], understanding=Understanding.not_demonstrated, covered_skill_ids=["python"]
    )
    base = inputs(github_linked=True, projects=[p])
    fid = flag_id_for(p.project_id, "understanding_gap")
    after = score(apply_changes(base, [SimulationChange(resolve_flags=[fid])]))
    assert audit(after, "campus-api").understanding == Understanding.demonstrated
    assert after.breakdown.total > score(base).breakdown.total


def test_set_understanding_and_set_skill_level():
    p = code_project(
        skills=["python"], signals=sig(authored_commits=3, total_commits=3), covered_skill_ids=["python"]
    )
    base = inputs(github_linked=True, projects=[p])
    shown = score(
        apply_changes(
            base, [SimulationChange(project_id=p.project_id, set_understanding=Understanding.demonstrated)]
        )
    )
    assert level(score(base), "python") == "moderate" and level(shown, "python") == "strong"
    lifted = SimulationChange(set_skill_level=SkillLevelChange(skill_id="docker", level=EvidenceLevel.strong))
    after = score(apply_changes(base, [lifted]))
    assert level(after, "docker") == "strong" and after.breakdown.total > score(base).breakdown.total
    assert next(c for c in after.claims if c.skill_id == "docker").reason == "Set to strong for a what-if"


@pytest.mark.parametrize(
    "change",
    [
        SimulationChange(project_id="proj-nope", add_signals=["tests"]),
        SimulationChange(resolve_flags=["flag-nope"]),
        SimulationChange(
            project_id="proj-campus-api", set_understanding=Understanding.demonstrated
        ).model_copy(update={"project_id": None}),
        SimulationChange(set_skill_level=SkillLevelChange(skill_id="cobol", level=EvidenceLevel.strong)),
        SimulationChange(set_skill_level=SkillLevelChange(skill_id="python")),
    ],
)
def test_unknown_or_incomplete_changes_raise(change):
    with pytest.raises(SimulationError):
        simulate(one_repo(), SimulationRequest(changes=[change]))


def test_signals_cannot_be_added_to_a_design_item():
    base = inputs(role="ui-ux-designer", projects=[design_project()])
    with pytest.raises(SimulationError, match="no repository signals"):
        apply_changes(
            base, [SimulationChange(project_id="proj-transit-app-case-study", add_signals=["tests"])]
        )


def test_gain_helpers_never_return_a_negative_number():
    base = one_repo()
    assert changes_gain(base, []) == 0.0
    already = one_repo(has_tests=True)
    assert (
        changes_gain(already, [SimulationChange(project_id="proj-campus-api", add_signals=["tests"])]) == 0.0
    )
    assert (
        changes_gain(base, [SimulationChange(project_id="proj-campus-api", add_signals=["tests", "ci"])]) > 0
    )
