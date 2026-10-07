from app import catalogue
from app.db.base import SessionLocal
from app.schemas.api import SimulationChange, Understanding
from app.services.llm import ProviderUnavailable
from app.services.planner import MAX_MILESTONES, MIN_MILESTONES, plan_roadmap
from app.services.scoring import changes_gain, flag_id_for, score
from tests.llm_fakes import SchemaProvider
from tests.scoring_helpers import code_project, inputs, rich_inputs, sig

ROLE = catalogue.get_role("sde-backend")
BASE = rich_inputs()
RESULT = score(BASE)
GAP_IDS = [g.gap_id for g in RESULT.gaps]
FLAG_ID = "flag-weather-dashboard-default-readme"
ALL_RESOURCE_URLS = {r.url for r in catalogue.load_resources()}


def milestone(
    addresses, resources=(), effort=4, title="Build something visible", deliverable="A repo that shows it"
):
    return {
        "title": title,
        "deliverable": deliverable,
        "addresses": list(addresses),
        "resource_ids": list(resources),
        "effort_hours": effort,
    }


def run(reply, base=BASE, result=RESULT):
    provider = SchemaProvider({"RoadmapPlan": reply})
    with SessionLocal() as db:
        milestones, notes = plan_roadmap(base, result, ROLE, db, providers=[provider], refresh=True)
    return milestones, notes, provider


def resource_for(gap_index):
    return catalogue.resources_for(RESULT.gaps[gap_index].skill_id)[0].id


def test_a_valid_plan_gets_real_resources_gains_ids_and_order():
    plan = {
        "milestones": [
            milestone([GAP_IDS[0]], [resource_for(0)], effort=6),
            milestone([FLAG_ID], effort=2),
            milestone([GAP_IDS[1]], [resource_for(1)], effort=3),
            milestone([GAP_IDS[2], GAP_IDS[3]], [resource_for(2)], effort=8),
        ]
    }
    milestones, notes, provider = run({"milestones": plan["milestones"]})
    assert notes == [] and len(milestones) == 4
    assert [m.id for m in milestones] == ["ms-1", "ms-2", "ms-3", "ms-4"]
    assert [m.order for m in milestones] == [1, 2, 3, 4] and not any(m.done for m in milestones)

    per_hour = [m.estimated_gain / m.effort_hours for m in milestones]
    assert per_hour == sorted(per_hour, reverse=True)  # gain per hour of effort, best first

    for m in milestones:
        assert all(r.url in ALL_RESOURCE_URLS for r in m.resources)  # URLs come from resources.yaml only
    two_gaps = next(m for m in milestones if len(m.addresses) == 2)
    both = [
        SimulationChange(set_skill_level={"skill_id": g.skill_id, "level": "strong"})
        for g in RESULT.gaps[2:4]
    ]
    assert two_gaps.estimated_gain == changes_gain(
        BASE, both
    )  # one recomputation over everything it addresses
    readme = next(m for m in milestones if m.addresses == [FLAG_ID])
    assert readme.estimated_gain == changes_gain(BASE, [SimulationChange(resolve_flags=[FLAG_ID])]) > 0

    assert provider.calls[0]["model"] == "fake-fast"
    assert all(g in provider.prompts for g in GAP_IDS[:4]) and FLAG_ID in provider.prompts


def test_unknown_ids_are_dropped_and_urls_in_text_are_removed():
    bad = milestone(
        ["gap-made-up"], ["fake-resource"], title="Learn it", deliverable="Read https://evil.example/guide"
    )
    ok = milestone(
        [GAP_IDS[0], "gap-made-up"],
        [resource_for(0), "fake-resource", "https://evil.example/x"],
        title="Ship it www.evil.example",
        deliverable="Publish a repo, see https://evil.example/guide for ideas",
    )
    milestones, _, _ = run({"milestones": [bad, ok]})
    first = next(m for m in milestones if m.addresses == [GAP_IDS[0]])
    assert [r.id for r in first.resources] == [resource_for(0)]
    assert (
        "evil" not in f"{first.title} {first.deliverable}"
        and first.deliverable == "Publish a repo, see for ideas"
    )
    assert all("gap-made-up" not in m.addresses for m in milestones)
    assert not any("Learn it" == m.title for m in milestones)  # nothing real to address: dropped


def test_at_most_seven_milestones_and_at_least_four():
    assert len(GAP_IDS) >= 4
    many = {"milestones": [milestone([GAP_IDS[i % len(GAP_IDS)]], effort=2 + i) for i in range(10)]}
    milestones, _, _ = run(many)
    assert len(milestones) == MAX_MILESTONES == 7

    one = {"milestones": [milestone([GAP_IDS[0]])]}
    topped_up, _, _ = run(one)
    assert len(topped_up) == MIN_MILESTONES == 4
    addressed = [a for m in topped_up for a in m.addresses]
    assert len(set(addressed)) == len(addressed)  # the extra milestones cover different things


def test_empty_or_unusable_model_output_falls_back_to_a_deterministic_roadmap():
    for reply in ({"milestones": []}, {"milestones": [milestone(["nope"])]}):
        milestones, notes, _ = run(reply)
        assert len(milestones) == MIN_MILESTONES and notes == []
        assert all(m.title and m.deliverable and m.addresses for m in milestones)


def test_planner_failure_never_fails_and_says_so():
    provider = SchemaProvider({"RoadmapPlan": ProviderUnavailable("429")})
    with SessionLocal() as db:
        milestones, notes = plan_roadmap(BASE, RESULT, ROLE, db, providers=[provider])
    assert len(milestones) == MIN_MILESTONES
    assert notes == [
        "The roadmap was built from the gaps and flags directly because the AI planner was unavailable."
    ]
    gap_milestone = next(m for m in milestones if m.addresses[0].startswith("gap-"))
    assert gap_milestone.resources and all(r.url in ALL_RESOURCE_URLS for r in gap_milestone.resources)
    assert gap_milestone.estimated_gain > 0

    invalid = SchemaProvider({"RoadmapPlan": "not json at all"})
    with SessionLocal() as db:
        again, again_notes = plan_roadmap(BASE, RESULT, ROLE, db, providers=[invalid])
    assert len(again) == MIN_MILESTONES and again_notes  # a bad reply twice is also a fallback


def test_an_understanding_gap_becomes_a_review_and_retake_milestone():
    p = code_project("campus-api", skills=["python"], signals=sig(authored_commits=10, total_commits=10))
    p.understanding, p.covered_skill_ids = Understanding.not_demonstrated, ["python"]
    base = inputs(github_linked=True, projects=[p])
    result = score(base)
    fid = flag_id_for(p.project_id, "understanding_gap")

    provider = SchemaProvider({"RoadmapPlan": ProviderUnavailable("down")})
    with SessionLocal() as db:
        milestones, _ = plan_roadmap(base, result, ROLE, db, providers=[provider])
    review = next(m for m in milestones if m.addresses == [fid])
    assert review.title == "Review campus-api and retake the check" and review.estimated_gain > 0

    # a model that skips it still gets the milestone added
    skipping = SchemaProvider(
        {"RoadmapPlan": {"milestones": [milestone([g.gap_id]) for g in result.gaps[:5]]}}
    )
    with SessionLocal() as db:
        planned, _ = plan_roadmap(base, result, ROLE, db, providers=[skipping])
    assert any(m.addresses == [fid] for m in planned) and len(planned) <= MAX_MILESTONES
    assert f"{fid} | campus-api | understanding_gap" in skipping.prompts


def test_nothing_to_improve_means_no_roadmap_and_no_llm_call():
    done = RESULT.model_copy(update={"gaps": [], "projects": []})
    milestones, notes, provider = run({"milestones": []}, result=done)
    assert (milestones, notes, provider.calls) == ([], [], [])


def test_the_prompt_carries_the_catalogue_and_no_links():
    _, _, provider = run({"milestones": [milestone([GAP_IDS[0]])]})
    prompt = provider.calls[0]["user"]
    assert "RESOURCE CATALOGUE" in prompt and resource_for(0) in prompt
    assert "http" not in prompt and "TARGET ROLE: Backend Developer" in prompt
    assert f"CURRENT SCORE: {RESULT.breakdown.total:g}" in prompt
