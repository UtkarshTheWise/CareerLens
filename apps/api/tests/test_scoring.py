"""Evidence levels, quiz effects and the five components (docs/SCORING.md §1-§3, §6)."""

from datetime import timedelta

import pytest

from app import catalogue
from app.schemas.api import Band, Confidence, Understanding
from app.schemas.llm import ResumeProject
from app.services.detectors import depth_parts, depth_points
from app.services.scoring import (
    CREDIT,
    _band,
    confidence_for,
    is_quantified,
    score,
)
from app.services.scoring_inputs import DesignInput
from tests.scoring_helpers import (
    PERFECT,
    TODAY,
    code_project,
    design_project,
    experience,
    flag,
    inputs,
    resume,
    sig,
    steady_weeks,
)

ROLE = catalogue.get_role("sde-backend")


def level_of(result, skill_id: str) -> str:
    return next(c.level.value for c in result.claims if c.skill_id == skill_id)


def component(result, key: str):
    return next(c for c in result.breakdown.components if c.key == key)


def project(result, title: str):
    return next(p for p in result.projects if p.title == title)


# ---------------------------------------------------------------- helpers


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Cut latency by 35%", True),
        ("Reached 3x throughput", True),
        ("Handled 10,000 requests", True),
        ("Wrote 40 tests", True),
        ("Built it in 2024", False),  # a year is not a result
        ("Joined in 2019-2021", False),
        ("Fixed 3 bugs", False),  # one digit with no % or x
        ("Improved performance", False),
    ],
)
def test_is_quantified(text, expected):
    assert is_quantified(text) is expected


@pytest.mark.parametrize(
    ("total", "band"),
    [
        (0, Band.not_ready),
        (49.9, Band.not_ready),
        (50.0, Band.developing),
        (74.9, Band.developing),
        (75.0, Band.ready),
        (100, Band.ready),
    ],
)
def test_band_boundaries(total, band):
    assert _band(total) == band


def test_depth_parts_sum_to_depth_points():
    s = sig(authored_commits=15, active_span_weeks=2, code_kb=10)
    assert depth_parts(s) == pytest.approx((4.0, 3.0, 3.0))
    assert depth_points(s) == pytest.approx(10.0)


def test_credits_follow_scoring_md():
    assert CREDIT == {"strong": 1.0, "moderate": 0.70, "weak": 0.35, "unverified": 0.10, "missing": 0.0}


# ---------------------------------------------------------------- evidence levels (§1)


def lvl(project, skill="python", **kw):
    return level_of(score(inputs(github_linked=True, projects=[project], **kw)), skill)


def test_strong_needs_5_commits_and_40_percent_in_a_non_fork():
    ok = sig(authored_commits=5, total_commits=12, authored_share=5 / 12)
    assert lvl(code_project(skills=["python"], signals=ok)) == "strong"
    exactly_40 = sig(authored_commits=8, total_commits=20, authored_share=0.40)
    assert lvl(code_project(skills=["python"], signals=exactly_40)) == "strong"
    four_commits = sig(authored_commits=4, total_commits=4, authored_share=1.0)
    assert lvl(code_project(skills=["python"], signals=four_commits)) == "moderate"
    low_share = sig(authored_commits=5, total_commits=13, authored_share=5 / 13)  # 38.5 %
    assert lvl(code_project(skills=["python"], signals=low_share)) == "moderate"


def test_forks_are_capped_at_moderate_and_untouched_forks_show_nothing():
    own_work = sig(
        is_fork=True, fork_authored_commits=30, authored_commits=30, total_commits=40, authored_share=0.75
    )
    assert lvl(code_project(skills=["python"], signals=own_work)) == "moderate"
    untouched = sig(
        is_fork=True, fork_authored_commits=0, authored_commits=40, total_commits=40, authored_share=1.0
    )
    assert lvl(code_project(skills=["python"], signals=untouched)) == "missing"


def test_main_language_or_topic_is_moderate():
    assert lvl(code_project(languages=["python"])) == "moderate"


def test_quantified_experience_bullet_is_moderate_unquantified_is_weak():
    quantified = resume(experience=[experience("Reduced latency by 35% with Redis caching")])
    assert level_of(score(inputs(resume=quantified)), "redis") == "moderate"
    plain = resume(experience=[experience("Added Redis caching to the booking service")])
    assert level_of(score(inputs(resume=plain)), "redis") == "weak"
    year_only = resume(experience=[experience("Built a Redis cache in 2024")])
    assert level_of(score(inputs(resume=year_only)), "redis") == "weak"


def test_weak_sources_are_project_text_linkedin_and_certificates():
    r = resume(
        projects=[
            ResumeProject(title="x", description="A bot using Docker", mentioned_technologies=["Redis"])
        ],
        certifications=[{"name": "Intro to SQL"}],
    )
    result = score(inputs(resume=r, has_linkedin=True, linkedin_skill_ids=["kubernetes"]))
    assert {level_of(result, s) for s in ("docker", "redis", "sql", "kubernetes")} == {"weak"}


def test_skills_list_alone_is_unverified_and_unclaimed_requirements_are_missing():
    result = score(inputs(resume=resume(skills=["Python"])))
    assert level_of(result, "python") == "unverified"
    assert level_of(result, "redis") == "missing"
    claim = next(c for c in result.claims if c.skill_id == "redis")
    assert claim.claimed is False and "not claimed" in claim.reason


def test_best_evidence_wins():
    r = resume(skills=["Python", "Docker"])
    result = score(
        inputs(
            resume=r,
            projects=[code_project(skills=["python"], signals=sig(authored_commits=2, total_commits=2))],
        )
    )
    assert level_of(result, "python") == "moderate"  # listed (unverified) + detector (moderate)
    assert level_of(result, "docker") == "unverified"


def test_unknown_listed_skills_are_noted_not_scored():
    result = score(inputs(resume=resume(skills=["Python", "Communication", "MS Teams"])))
    assert all(c.skill_name not in ("Communication", "MS Teams") for c in result.claims)
    assert any("not in the catalogue and were not scored: Communication, MS Teams" in n for n in result.notes)


def test_design_tools_need_a_case_study():
    designer = {"role": "ui-ux-designer"}
    seen = design_project()
    assert level_of(score(inputs(projects=[seen], **designer)), "figma") == "moderate"
    no_case_study = DesignInput(
        problem_statement=0, process_evidence=0, outcome_or_metrics=5, tools_seen=["Figma"]
    )
    assert (
        level_of(score(inputs(projects=[design_project(design=no_case_study)], **designer)), "figma")
        == "missing"
    )
    claimed_only = design_project(design=no_case_study, claimed_skill_ids=["figma"])
    assert level_of(score(inputs(projects=[claimed_only], **designer)), "figma") == "weak"
    unreadable = DesignInput(readable=False, tools_seen=["Figma"])
    assert (
        level_of(score(inputs(projects=[design_project(design=unreadable)], **designer)), "figma")
        == "missing"
    )


# ---------------------------------------------------------------- quiz effects (§6)

STRONG_REPO = sig(authored_commits=3, total_commits=3, authored_share=1.0)  # moderate: below 5 commits


def with_quiz(understanding, covered=("python",), **kw):
    return code_project(
        skills=["python", "sql"],
        signals=STRONG_REPO,
        understanding=understanding,
        covered_skill_ids=list(covered),
        **kw,
    )


def test_demonstrated_raises_covered_moderate_skills_only():
    result = score(inputs(github_linked=True, projects=[with_quiz(Understanding.demonstrated)]))
    assert level_of(result, "python") == "strong"
    assert level_of(result, "sql") == "moderate"  # not covered by the quiz


def test_demonstrated_adds_five_authorship_points_capped_at_30():
    def authorship(understanding, share):
        s = sig(authored_commits=3, total_commits=3, authored_share=share)
        p = code_project(skills=["python"], signals=s, understanding=understanding)
        return project(score(inputs(projects=[p])), "campus-api").subscores.authorship

    # share 0.4 -> 7.5 + original 5 + no flags 10 = 22.5, then +5 for a demonstrated quiz
    assert authorship(Understanding.not_taken, 0.4) == 22.5
    assert authorship(Understanding.demonstrated, 0.4) == 27.5
    # already at 30: the bonus is capped
    assert authorship(Understanding.not_taken, 1.0) == 30
    assert authorship(Understanding.demonstrated, 1.0) == 30


def test_not_demonstrated_lowers_sole_evidence_and_adds_a_flag():
    strong = sig(authored_commits=10, total_commits=10, authored_share=1.0)
    p = code_project(
        skills=["python"],
        signals=strong,
        understanding=Understanding.not_demonstrated,
        covered_skill_ids=["python"],
    )
    result = score(inputs(github_linked=True, projects=[p]))
    assert level_of(result, "python") == "moderate"  # strong -> moderate
    flags = project(result, "campus-api").flags
    assert [f.code for f in flags] == ["understanding_gap"] and flags[0].estimated_gain > 0
    assert "demonstrated" not in flags[0].reason.lower() or "not" in flags[0].reason.lower()


def test_not_demonstrated_leaves_skills_backed_by_other_evidence():
    strong = sig(authored_commits=10, total_commits=10, authored_share=1.0)
    gap = code_project(
        "weak-one",
        skills=["python"],
        signals=strong,
        understanding=Understanding.not_demonstrated,
        covered_skill_ids=["python"],
    )
    other = code_project("other-repo", skills=["python"], signals=strong)
    assert level_of(score(inputs(github_linked=True, projects=[gap, other])), "python") == "strong"


def test_skills_list_does_not_count_as_other_evidence_for_the_drop():
    strong = sig(authored_commits=10, total_commits=10, authored_share=1.0)
    p = code_project(
        skills=["python"],
        signals=strong,
        understanding=Understanding.not_demonstrated,
        covered_skill_ids=["python"],
    )
    result = score(inputs(github_linked=True, resume=resume(skills=["Python"]), projects=[p]))
    assert level_of(result, "python") == "moderate"


@pytest.mark.parametrize("understanding", [Understanding.not_taken, Understanding.partial])
def test_not_taken_and_partial_change_nothing(understanding):
    base = score(inputs(github_linked=True, projects=[with_quiz(Understanding.not_taken)]))
    other = score(inputs(github_linked=True, projects=[with_quiz(understanding)]))
    assert other.breakdown == base.breakdown and other.claims == base.claims


def test_design_demonstrated_lifts_weak_to_moderate_never_to_strong():
    item = design_project(
        design=DesignInput(problem_statement=10, process_evidence=10, tools_seen=[]),
        claimed_skill_ids=["figma"],
        understanding=Understanding.demonstrated,
        covered_skill_ids=["figma"],
    )
    assert level_of(score(inputs(role="ui-ux-designer", projects=[item])), "figma") == "moderate"
    seen = design_project(understanding=Understanding.demonstrated, covered_skill_ids=["figma"])
    assert (
        level_of(score(inputs(role="ui-ux-designer", projects=[seen])), "figma") == "moderate"
    )  # stays moderate


def test_design_score_moves_five_points_with_the_quiz_within_the_cap():
    def design_score(rubric_total_design: DesignInput, understanding):
        p = design_project(design=rubric_total_design, understanding=understanding)
        return project(score(inputs(role="ui-ux-designer", projects=[p])), p.title).score

    sixty = DesignInput(problem_statement=25, process_evidence=30, outcome_or_metrics=5)
    assert design_score(sixty, Understanding.not_taken) == 60
    assert design_score(sixty, Understanding.demonstrated) == 65
    assert design_score(sixty, Understanding.not_demonstrated) == 55
    full = DesignInput(
        problem_statement=25, process_evidence=30, outcome_or_metrics=20, tool_evidence=15, presentation=10
    )
    assert design_score(full, Understanding.not_taken) == 80  # self-reported cap
    assert design_score(full, Understanding.demonstrated) == 80


# ---------------------------------------------------------------- component A


def test_component_a_formula_and_positive_deltas_sum_to_score():
    r = resume(skills=["Python", "SQL"])
    result = score(inputs(resume=r, github_linked=True, projects=[code_project(skills=["docker", "redis"])]))
    total_w = sum(rs.importance for rs in ROLE.skills)
    expected = (
        100 * sum(rs.importance * CREDIT[level_of(result, rs.skill_id)] for rs in ROLE.skills) / total_w
    )
    a = component(result, "skill_evidence")
    assert a.score == pytest.approx(expected, abs=0.06)
    assert sum(x.delta for x in a.reasons if x.delta > 0) == pytest.approx(a.score, abs=0.1)
    withheld = [x for x in a.reasons if x.delta < 0]
    assert withheld and all("no evidence yet" in x.text for x in withheld)


# ---------------------------------------------------------------- component B: project quality


def test_a_perfect_project_scores_100_and_an_empty_one_15():
    perfect = score(inputs(projects=[code_project("great", signals=sig(**PERFECT))]))
    p = project(perfect, "great")
    assert p.score == 100
    assert (p.subscores.hygiene, p.subscores.engineering, p.subscores.authorship, p.subscores.depth) == (
        20,
        30,
        30,
        20,
    )
    bare = project(
        score(
            inputs(
                projects=[
                    code_project(
                        "bare",
                        signals=sig(
                            authored_commits=0, total_commits=0, authored_share=0.0, commit_facts_known=False
                        ),
                    )
                ]
            )
        ),
        "bare",
    )
    assert bare.score == 15  # not a fork (5) + no flags (10)
    assert (
        bare.subscores.hygiene,
        bare.subscores.engineering,
        bare.subscores.authorship,
        bare.subscores.depth,
    ) == (0, 0, 15, 0)


@pytest.mark.parametrize(("share", "points"), [(0.0, 0), (0.2, 0), (0.4, 7.5), (0.6, 15), (0.8, 15)])
def test_authored_share_is_linear_from_20_to_60_percent(share, points):
    s = sig(authored_share=share, authored_commits=0)
    p = project(score(inputs(projects=[code_project(signals=s)])), "campus-api")
    assert p.subscores.authorship == pytest.approx(points + 5 + 10)


def test_first_two_flags_each_cost_five_authorship_points_and_it_never_goes_below_zero():
    s = sig(
        authored_share=0.0, authored_commits=0, is_fork=True, fork_authored_commits=0
    )  # forks earn 0 for originality
    scores = []
    for n in range(0, 5):
        flags = [flag(c) for c in ("single_dump", "default_readme", "tutorial_pattern", "thin_wrapper")[:n]]
        scores.append(
            project(
                score(inputs(projects=[code_project(signals=s, flags=flags)])), "campus-api"
            ).subscores.authorship
        )
    assert scores[:4] == [10, 5, 0, 0]
    assert scores[4] == 0  # a fifth flag cannot push it below zero


def test_fork_originality_needs_five_own_commits():
    def authorship(own):
        s = sig(is_fork=True, fork_authored_commits=own, authored_share=0.0, authored_commits=own)
        return project(score(inputs(projects=[code_project(signals=s)])), "campus-api").subscores.authorship

    assert authorship(5) - authorship(4) == 5


def test_depth_items_are_linear():
    s = sig(authored_commits=15, active_span_weeks=2, code_kb=10)
    assert project(
        score(inputs(projects=[code_project(signals=s)])), "campus-api"
    ).subscores.depth == pytest.approx(10)


def test_top_three_projects_by_relevance_not_by_score():
    best = code_project("showpiece", signals=sig(**PERFECT))  # highest score, no skills relevant to the role
    projects = [
        code_project("backend", skills=["python", "sql"]),  # relevance 3 + 3
        code_project("infra", skills=["redis", "aws"]),  # 2 + 2
        code_project("tiny", skills=["docker"]),  # 2
        best,
    ]
    result = score(inputs(github_linked=True, projects=projects))
    counted = {p.title for p in result.projects if p.counted_in_score}
    assert counted == {"backend", "infra", "tiny"}
    scores = [p.score for p in result.projects if p.counted_in_score]
    assert component(result, "project_quality").score == pytest.approx(sum(scores) / 3, abs=0.06)


def test_design_cap_and_design_role_without_portfolio():
    full = DesignInput(
        problem_statement=25, process_evidence=30, outcome_or_metrics=20, tool_evidence=15, presentation=10
    )
    p = design_project(design=full)
    audit = project(score(inputs(role="ui-ux-designer", projects=[p])), p.title)
    assert audit.score == 80 and audit.self_reported and audit.design_subscores.process_evidence == 30
    assert audit.subscores is None and audit.signals is None

    unreadable = design_project(design=DesignInput(readable=False, problem_statement=25))
    assert project(score(inputs(role="ui-ux-designer", projects=[unreadable])), unreadable.title).score == 0

    repos_only = score(
        inputs(role="ui-ux-designer", github_linked=True, projects=[code_project(skills=["html-css"])])
    )
    b = component(repos_only, "project_quality")
    assert b.score == 0.0 and b.weight > 0  # a missing portfolio is penalised, not "no data"


def test_engineering_role_with_no_projects_is_no_data():
    b = component(score(inputs()), "project_quality")
    assert b.score is None and b.weight == 0.0 and b.contribution == 0.0


# ---------------------------------------------------------------- component C: consistency


def consistency(**kw):
    result = score(inputs(github_linked=True, **kw))
    return component(result, "consistency").score, result.consistency


def test_steady_recent_activity_scores_100():
    value, summary = consistency(weeks=steady_weeks(5), last_active_date=TODAY - timedelta(days=7))
    assert value == 100 and summary.active_weeks == 26 and summary.cv == 0


def test_active_ratio_stability_and_recency_are_weighted_50_30_20():
    counts = [10 if i % 2 == 0 else 0 for i in range(26)]  # 13 active weeks, mean 5, std 5, cv 1
    weeks = [w.model_copy(update={"count": c}) for w, c in zip(steady_weeks(), counts, strict=True)]
    value, summary = consistency(weeks=weeks, last_active_date=TODAY - timedelta(days=14))
    assert summary.active_weeks == 13 and summary.cv == 1.0
    assert value == pytest.approx(100 * (0.5 * 13 / 26 + 0.3 * (1 - 1 / 2) + 0.2 * 1), abs=0.06)


@pytest.mark.parametrize(("days", "recency"), [(0, 1.0), (14, 1.0), (52, 0.5), (90, 0.0), (400, 0.0)])
def test_recency_falls_linearly_from_14_to_90_days(days, recency):
    value, _ = consistency(weeks=steady_weeks(5), last_active_date=TODAY - timedelta(days=days))
    assert value == pytest.approx(100 * (0.5 + 0.3) + 20 * recency, abs=0.06)


def test_no_activity_scores_zero_and_missing_weeks_count_as_idle():
    value, summary = consistency(weeks=[], last_active_date=None)
    assert value == 0 and summary.cv is None and summary.active_weeks == 0
    value, summary = consistency(weeks=steady_weeks(5, n=13), last_active_date=TODAY)
    assert summary.active_weeks == 13  # a 13-week-old account is padded to 26 weeks


def test_consistency_is_no_data_without_github():
    c = component(score(inputs(github_linked=False)), "consistency")
    assert c.score is None and c.weight == 0.0
    assert score(inputs(github_linked=False)).consistency is None


# ---------------------------------------------------------------- components D and E


def exp_score(*experiences):
    return component(score(inputs(resume=resume(experience=list(experiences)))), "experience").score


def test_experience_roles_and_quantified_ratio():
    assert exp_score() == 0
    assert exp_score(experience()) == pytest.approx(36)  # one role, no bullets: 60 x 0.6
    assert exp_score(experience("Cut latency by 35%", "Wrote 40 tests")) == pytest.approx(60)
    assert exp_score(experience("Cut latency by 35%", "Wrote docs")) == pytest.approx(60 * 0.8)
    two_quantified = [experience("Cut latency by 35%"), experience("Served 10,000 users", org="Other")]
    assert exp_score(*two_quantified) == pytest.approx(100)
    two_plain = [experience("Helped the team"), experience("Fixed things", org="Other")]
    assert exp_score(*two_plain) == pytest.approx(60)


def resume_score(r, **kw):
    return component(score(inputs(resume=r, **kw)), "resume_quality").score


FULL_RESUME = dict(
    skills=["Python", "SQL"],
    education=[{"institution": "X"}],
    experience=[experience("Cut latency by 35%")],
    projects=[
        {"title": "p", "description": "Handled 10,000 requests", "mentioned_technologies": ["Python", "SQL"]}
    ],
    page_count_hint=1,
)


def test_resume_quality_items():
    r = resume(**FULL_RESUME)
    evidenced = [code_project(skills=["python", "sql"])]
    assert resume_score(r, projects=evidenced, github_linked=True) == pytest.approx(100)  # 40 + 30 + 15 + 15
    assert resume_score(resume(**{**FULL_RESUME, "page_count_hint": 3}), projects=evidenced) == pytest.approx(
        85
    )
    assert resume_score(
        resume(**{**FULL_RESUME, "page_count_hint": None}), projects=evidenced
    ) == pytest.approx(100)
    assert resume_score(r, projects=evidenced, has_contact=False) == pytest.approx(92)
    no_numbers = resume(
        **{
            **FULL_RESUME,
            "experience": [experience("Helped")],
            "projects": [{"title": "p", "description": "A site", "mentioned_technologies": []}],
        }
    )
    assert resume_score(no_numbers, projects=evidenced) == pytest.approx(70)


def test_unknown_page_count_is_noted_not_penalised():
    result = score(inputs(resume=resume(**{**FULL_RESUME, "page_count_hint": None})))
    assert any("page count is unknown" in n for n in result.notes)


def test_skills_list_inflation_rules():
    # the project text names no skills, so only the skills list and the repos decide the levels
    plain = {**FULL_RESUME, "projects": [{"title": "p", "description": "Handled 10,000 requests"}]}

    def quality(skills, repo_skills):
        r = resume(**{**plain, "skills": skills})
        return resume_score(r, github_linked=True, projects=[code_project(skills=repo_skills)])

    assert quality([f"Python{i}" for i in range(26)] + ["Python"], ["python"]) == pytest.approx(
        85
    )  # list > 25
    assert quality(["Python", "Docker"], ["python"]) == pytest.approx(85)  # 50 % unverified is not < 50 %
    assert quality(["Python", "SQL", "Docker"], ["python", "sql"]) == pytest.approx(100)  # a third unverified
    assert quality([], []) == pytest.approx(100 - 8 - 15)  # no skills section and no inflation credit


# ---------------------------------------------------------------- aggregation: missing data, confidence, cap


def weights_of(result):
    return {c.key: c.weight for c in result.breakdown.components}


def test_default_weights_with_all_data():
    result = score(inputs(github_linked=True, projects=[code_project()], resume=resume(**FULL_RESUME)))
    assert weights_of(result) == {
        "skill_evidence": 0.4, "project_quality": 0.25, "consistency": 0.15, "experience": 0.1, "resume_quality": 0.1,
    }  # fmt: skip


def test_no_github_redistributes_weights_lowers_confidence_and_caps_at_60():
    bullets = [
        "Built REST APIs in Python and FastAPI on SQL, cutting latency by 40%",
        "Containerised services with Docker and wrote 40 pytest tests; used Git daily",
        "Added Redis caching and moved the jobs to AWS, saving 20% cost",
    ]
    r = resume(**{**FULL_RESUME, "experience": [experience(*bullets), experience(*bullets, org="Other")]})
    result = score(inputs(resume=r))
    weights = weights_of(result)
    assert weights["consistency"] == 0 and weights["project_quality"] == 0
    assert sum(weights.values()) == pytest.approx(1.0, abs=0.001)
    assert weights["skill_evidence"] == pytest.approx(
        0.4 / 0.6, abs=0.001
    )  # shared in proportion to the originals
    assert result.breakdown.confidence == Confidence.low
    assert result.breakdown.capped is True and result.breakdown.total == 60.0
    assert any("capped at 60" in n for n in result.notes) and any(
        "No data for project quality and consistency" in n or "No data for" in n for n in result.notes
    )


def test_cap_only_flags_scores_it_actually_lowered():
    result = score(inputs(resume=resume(skills=["Python"])))
    assert result.breakdown.confidence == Confidence.low and result.breakdown.capped is False
    assert result.breakdown.total < 60


def test_designer_without_github_is_not_penalised():
    item = design_project()
    result = score(
        inputs(role="ui-ux-designer", resume=resume(**{**FULL_RESUME, "skills": ["Figma"]}), projects=[item])
    )
    weights = weights_of(result)
    assert weights["consistency"] == 0 and weights["project_quality"] == pytest.approx(0.30 / 0.95, abs=0.001)
    assert sum(weights.values()) == pytest.approx(1.0, abs=0.001)
    assert result.breakdown.confidence == Confidence.medium and not result.breakdown.capped
    assert component(result, "project_quality").score == 70.0
    assert any("consistency" in n for n in result.notes)


def test_designer_without_portfolio_is_penalised():
    result = score(inputs(role="ui-ux-designer", github_linked=True, resume=resume(**FULL_RESUME)))
    b = component(result, "project_quality")
    assert b.score == 0.0 and b.weight == pytest.approx(0.30)  # real data (zero), nothing redistributed away


def test_confidence_rules():
    designer = catalogue.get_role("ui-ux-designer")
    portfolio = [design_project()]
    assert confidence_for(inputs(), ROLE) == Confidence.low
    assert confidence_for(inputs(github_linked=True), ROLE) == Confidence.medium
    assert confidence_for(inputs(has_linkedin=True), ROLE) == Confidence.medium
    assert confidence_for(inputs(github_linked=True, has_linkedin=True), ROLE) == Confidence.high
    assert confidence_for(inputs(github_linked=True, projects=portfolio), ROLE) == Confidence.high
    assert (
        confidence_for(inputs(has_linkedin=True, projects=portfolio), ROLE) == Confidence.medium
    )  # no GitHub
    assert (
        confidence_for(inputs(has_linkedin=True, projects=portfolio), designer) == Confidence.high
    )  # designers need none
    assert confidence_for(inputs(projects=portfolio), designer) == Confidence.medium


def test_total_is_the_sum_of_contributions_and_band_follows_it():
    result = score(
        inputs(
            github_linked=True,
            has_linkedin=True,
            projects=[code_project(skills=["python"])],
            resume=resume(**FULL_RESUME),
            weeks=steady_weeks(5),
            last_active_date=TODAY,
        )
    )
    b = result.breakdown
    assert b.total == pytest.approx(sum(c.contribution for c in b.components), abs=0.1)
    assert b.band == _band(b.total)
    assert result.coverage == 50.0  # python (moderate) of python + sql


def test_coverage_is_strong_or_moderate_over_claimed_catalogue_skills():
    r = resume(skills=["Python", "SQL", "Docker", "Kubernetes"])
    result = score(inputs(resume=r, github_linked=True, projects=[code_project(skills=["python", "sql"])]))
    assert result.coverage == 50.0
    nothing = score(inputs())
    assert nothing.coverage == 0.0 and any("Evidence Coverage is 0" in n for n in nothing.notes)
