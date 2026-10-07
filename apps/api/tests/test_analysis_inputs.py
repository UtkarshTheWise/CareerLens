import pytest

from app import catalogue
from app.db.base import SessionLocal
from app.schemas.api import Understanding
from app.schemas.llm import ProjectJudgement, ResumeProfile, ResumeProject
from app.services.analysis_inputs import (
    MAX_JUDGED,
    DesignItem,
    build_project_inputs,
    carry_understanding,
    claimed_skill_ids,
    judge_design_item,
    judge_project,
    judgement_flags,
    match_resume_projects,
    select_for_review,
)
from app.services.detectors import DetectorHit, RepoAnalysis, RepoSignals, RuleFlag
from app.services.github import GithubSnapshot, RepoData
from app.services.portfolio import PageText
from app.services.scoring_inputs import DesignInput
from tests.llm_fakes import SchemaProvider, design_judgement, project_judgement

ROLE = catalogue.get_role("sde-backend")


def repo(name, *, fork=False, own=10, **kw) -> RepoData:
    return RepoData(
        name=name,
        url=f"https://github.com/careerlens-demo/{name}",
        is_fork=fork,
        authored_since_created=own,
        authored_commits=own,
        total_commits=max(own, 12),
        has_commit_facts=True,
        **kw,
    )


def analysis(name, skills=(), **signal_kw) -> RepoAnalysis:
    return RepoAnalysis(
        repo_name=name,
        skills={s: [DetectorHit(kind="pip", detail=s)] for s in skills},
        signals=RepoSignals(authored_commits=10, total_commits=12, **signal_kw),
    )


def rp(title, links=(), description="", techs=()) -> ResumeProject:
    return ResumeProject(
        title=title, description=description, links=list(links), mentioned_technologies=list(techs)
    )


# ---------------------------------------------------------------- matching


def test_match_by_repo_url_ignores_case_slash_and_dot_git():
    repos = [repo("campus-api"), repo("weather-dashboard")]
    resume = ResumeProfile(
        projects=[
            rp("Event system", ["HTTPS://GitHub.com/CareerLens-Demo/Campus-API.git/"]),
            rp("Weather", ["https://github.com/careerlens-demo/weather-dashboard"]),
        ]
    )
    matched = match_resume_projects(resume, repos)
    assert matched["campus-api"].title == "Event system" and matched["weather-dashboard"].title == "Weather"


@pytest.mark.parametrize("title", ["campus-api", "Campus API", "campus_api", "CampusAPI", "campus-apı"[:10]])
def test_match_by_normalised_name(title):
    matched = match_resume_projects(ResumeProfile(projects=[rp(title)]), [repo("campus-api")])
    assert "campus-api" in matched


def test_similar_but_different_names_do_not_match():
    resume = ResumeProfile(projects=[rp("weather-app"), rp("chat")])
    assert match_resume_projects(resume, [repo("weather-dashboard"), repo("chatbot-ui")]) == {}


def test_matching_is_one_to_one_and_urls_beat_names():
    repos = [repo("campus-api"), repo("campus-api-v2")]
    resume = ResumeProfile(
        projects=[rp("campus-api", ["https://github.com/careerlens-demo/campus-api-v2"]), rp("campus api")]
    )
    matched = match_resume_projects(resume, repos)
    assert matched["campus-api-v2"].links  # the URL decides
    assert matched["campus-api"].links == []  # the other project takes the other repo
    assert len(matched) == 2
    assert match_resume_projects(
        ResumeProfile(projects=[rp("campus-api"), rp("campus-api")]), [repo("campus-api")]
    ).keys() == {"campus-api"}


def test_claimed_skill_ids_from_technologies_and_description():
    p = rp("x", description="A REST API using Docker and a Redis cache", techs=["FastAPI", "Brainfuck"])
    assert claimed_skill_ids(p) == ["docker", "fastapi", "redis", "rest-api"]


# ---------------------------------------------------------------- choosing what to review


def snapshot(*repos) -> GithubSnapshot:
    return GithubSnapshot(login="careerlens-demo", user_id="X", repos=list(repos))


def test_review_selection_is_capped_matched_first_then_relevant():
    repos = [repo(f"proj{i}") for i in range(8)] + [repo("on-resume")]
    analyses = {
        r.name: analysis(
            r.name, skills=["python", "sql"] if r.name == "proj5" else ["docker"] if r.name == "proj1" else []
        )
        for r in repos
    }
    chosen = select_for_review(snapshot(*repos), analyses, {"on-resume": rp("on-resume")}, ROLE)
    assert len(chosen) == MAX_JUDGED == 6
    assert chosen[:3] == [
        "on-resume",
        "proj5",
        "proj1",
    ]  # resume first, then relevance (python+sql, then docker)
    assert chosen[3:] == ["proj0", "proj2", "proj3"]  # then by name


def test_untouched_forks_and_unanalysed_repos_are_never_reviewed():
    repos = [
        repo("mine"),
        repo("untouched", fork=True, own=0),
        repo("improved-fork", fork=True, own=7),
        repo("old"),
    ]
    analyses = {n: analysis(n) for n in ("mine", "untouched", "improved-fork")}  # "old" has no analysis
    assert select_for_review(snapshot(*repos), analyses, {}, ROLE) == ["improved-fork", "mine"]


# ---------------------------------------------------------------- the project judge


def run_judge(readme="# Campus API\nA REST API.", description="Event registration API", **kw):
    provider = SchemaProvider({"ProjectJudgement": project_judgement()})
    r = repo("campus-api", readme=readme, license="MIT", homepage="https://demo.example.dev/priya")
    with SessionLocal() as db:
        judged = judge_project(
            r,
            analysis("campus-api", skills=["python", "fastapi"], has_tests=True, has_demo_url=True),
            rp("campus-api", description=description, techs=["FastAPI", "Redis"]),
            ROLE,
            student_name="Priya Raman",
            db=db,
            providers=[provider],
            refresh=False,
            **kw,
        )
    return judged, provider


def test_judge_prompt_has_the_facts_and_no_personal_data():
    readme = "# Campus API\nBy Priya Raman (priya.raman@example.com, +91 98765 43210).\nSource: github.com/priyaraman/campus-api"
    judged, provider = run_judge(readme=readme, description="Built by Priya Raman, call +91 98765 43210")
    prompt = provider.prompts
    for secret in ("priya", "raman", "example.com", "98765", "github.com/priyaraman", "demo.example.dev"):
        assert secret not in prompt.lower(), secret
    assert "TARGET ROLE: Backend Developer" in prompt
    assert "detected technologies: FastAPI, Python" in prompt
    assert (
        "authored commits: 10 of 12" in prompt and "tests: yes; CI: no; demo URL: yes; licence: MIT" in prompt
    )
    assert "TECHNOLOGIES THE STUDENT CLAIMS: FastAPI, Redis" in prompt
    assert "# Campus API" in prompt  # a README title is not mistaken for the student's name
    assert provider.calls[0]["model"] == "fake-smart"
    assert isinstance(judged, ProjectJudgement) and judged.specificity == 3


def test_a_repo_with_no_description_still_gets_a_prompt():
    provider = SchemaProvider({"ProjectJudgement": project_judgement()})
    with SessionLocal() as db:
        judge_project(
            repo("x"), analysis("x"), None, ROLE, student_name="", db=db, providers=[provider], refresh=False
        )
    assert "(no description written)" in provider.prompts and "(none detected)" in provider.prompts


# ---------------------------------------------------------------- flags from the judgement


def judged(**kw) -> ProjectJudgement:
    return ProjectJudgement.model_validate(project_judgement(**kw))


@pytest.mark.parametrize(
    ("specificity", "metric", "flagged"),
    [(0, False, True), (1, False, True), (2, False, False), (1, True, False), (0, True, False)],
)
def test_vague_description_is_specificity_at_most_one_without_a_metric(specificity, metric, flagged):
    flags = judgement_flags(judged(specificity=specificity, has_metric=metric), set(), set())
    assert ("vague_description" in {f.code for f in flags}) is flagged


def test_claim_mismatch_needs_the_model_and_the_detectors_to_agree():
    claim = judged(unsupported_claims=["Redis"])
    both = judgement_flags(claim, claimed={"redis", "python"}, detected={"python"})
    assert [f.code for f in both] == ["claim_mismatch"] and "Redis" in both[0].reason
    assert both[0].severity == "medium" and "remove the claim" in both[0].fix

    assert judgement_flags(claim, {"redis"}, {"redis"}) == []  # a detector found it: the model is wrong
    assert judgement_flags(judged(), {"redis"}, set()) == []  # detectors alone are not enough
    assert judgement_flags(claim, {"python"}, set()) == []  # the student never claimed it
    assert (
        judgement_flags(judged(unsupported_claims=["Unobtainium"]), {"python"}, set()) == []
    )  # not a catalogue skill


def test_flag_wording_is_neutral():
    flags = judgement_flags(
        judged(specificity=0, has_metric=False, unsupported_claims=["Redis"]), {"redis"}, set()
    )
    text = " ".join(f"{f.reason} {f.fix}" for f in flags).lower()
    assert len(flags) == 2 and not any(w in text for w in ("slop", "fake", "dishonest", "ai-generated"))


# ---------------------------------------------------------------- the design judge


PAGE = PageText(
    url="https://behance.net/priyaraman/transit",
    readable=True,
    title="Transit app by Priya Raman",
    description="Case study",
    text="Priya Raman redesigned bus tickets. Research with 12 interviews in Figma.",
)


def run_design(page=PAGE, skills=("Figma", "Python")):
    provider = SchemaProvider({"DesignJudgement": design_judgement()})
    with SessionLocal() as db:
        item = judge_design_item(
            page,
            catalogue.get_role("ui-ux-designer"),
            ResumeProfile(skills=list(skills)),
            student_name="Priya Raman",
            db=db,
            providers=[provider],
            refresh=False,
        )
    return item, provider


def test_unreadable_pages_cost_no_llm_call_and_score_zero():
    page = PageText(url="https://x.dev", readable=False, reason="the page could not be reached")
    item, provider = run_design(page)
    assert provider.calls == [] and item.design == DesignInput(readable=False) and item.design.total == 0


def test_design_prompt_hides_the_link_and_the_name_and_lists_only_design_tools():
    item, provider = run_design()
    prompt = provider.prompts
    assert "priya" not in prompt.lower() and "behance" not in prompt.lower() and "(link removed)" in prompt
    assert "TOOLS THE STUDENT CLAIMS: Figma" in prompt  # Python is not a design tool
    assert (item.design.problem_statement, item.design.process_evidence, item.design.tools_seen) == (
        20,
        22,
        ["Figma"],
    )
    assert item.design.total == 72 and item.issues[0].fix.startswith("Add what changed")


# ---------------------------------------------------------------- assembling project inputs


def test_carry_understanding_reads_the_stored_result():
    stored = {
        "https://github.com/u/a": {
            "understanding": "demonstrated",
            "covered_skill_ids": ["python"],
            "quiz_id": "q1",
        }
    }
    assert carry_understanding("https://github.com/u/a", stored) == (
        Understanding.demonstrated,
        ["python"],
        "q1",
    )
    assert carry_understanding("https://github.com/u/b", stored) == (Understanding.not_taken, [], None)
    assert carry_understanding(None, {"": "junk"}) == (Understanding.not_taken, [], None)
    assert carry_understanding("u", {"u": {"understanding": "nonsense"}})[0] == Understanding.not_taken


def test_build_project_inputs_merges_flags_text_and_understanding():
    r = repo("campus-api")
    a = analysis("campus-api", skills=["python"])
    a.flags = [RuleFlag(code="single_dump", severity="medium", reason="r", fix="f")]
    resume_project = rp("campus-api", description="A REST API with Redis", techs=["Redis"])
    j = judged(specificity=1, has_metric=False, unsupported_claims=["Redis"])
    stored = {
        r.url: {
            "understanding": "not_demonstrated",
            "covered_skill_ids": ["python"],
            "quiz_id": "11111111-1111-1111-1111-111111111111",
        }
    }
    page = PageText(url="https://x.dev/a", readable=True, title="Case study", text="t" * 100)
    items = [
        DesignItem(page.url, page, DesignInput(problem_statement=5), []),
        DesignItem("https://x.dev/b", page, DesignInput(), []),
    ]

    projects, texts = build_project_inputs(
        snapshot(r), {"campus-api": a}, {"campus-api": resume_project}, {"campus-api": j}, items, stored
    )

    code = projects[0]
    assert (code.project_id, code.kind, code.title) == ("proj-campus-api", "code", "campus-api")
    assert [f.code for f in code.flags] == ["single_dump", "vague_description", "claim_mismatch"]
    assert code.claimed_skill_ids == ["redis", "rest-api"]
    assert code.understanding == Understanding.not_demonstrated and code.covered_skill_ids == ["python"]
    assert str(code.latest_quiz_id) == "11111111-1111-1111-1111-111111111111"
    assert texts["proj-campus-api"].what_it_does == j.what_it_does and texts["proj-campus-api"].issues

    assert [p.project_id for p in projects[1:]] == [
        "proj-case-study",
        "proj-case-study-2",
    ]  # duplicate titles stay unique
    assert all(p.kind == "design" for p in projects[1:])


def test_repos_without_an_analysis_are_not_projects():
    projects, _ = build_project_inputs(snapshot(repo("a"), repo("b")), {"a": analysis("a")}, {}, {}, [], {})
    assert [p.title for p in projects] == ["a"]
    assert build_project_inputs(None, {}, {}, {}, [], {}) == ([], {})


def test_a_repo_not_on_the_resume_is_described_by_its_tagline_and_readme_opening():
    provider = SchemaProvider({"ProjectJudgement": project_judgement()})
    readme = "# Habit tracker\n\nTracks daily goals offline in localStorage. " + "More detail. " * 100
    r = repo("habits", description="Daily habits", readme=readme)
    with SessionLocal() as db:
        judge_project(
            r, analysis("habits"), None, ROLE, student_name="", db=db, providers=[provider], refresh=False
        )
    user = provider.calls[0]["user"]
    section = user[user.index("STUDENT'S DESCRIPTION:") : user.index("TECHNOLOGIES THE STUDENT CLAIMS")]
    assert "Daily habits" in section and "Tracks daily goals offline in localStorage" in section
    assert len(section) < 900  # only the opening, not the whole README
    assert "(no description written)" not in user


def test_a_resume_description_wins_over_the_readme():
    provider = SchemaProvider({"ProjectJudgement": project_judgement()})
    r = repo("habits", description="tagline", readme="README text that must not be the description")
    with SessionLocal() as db:
        judge_project(
            r, analysis("habits"), rp("habits", description="Resume says: offline habit tracker"), ROLE,
            student_name="", db=db, providers=[provider], refresh=False,
        )  # fmt: skip
    user = provider.calls[0]["user"]
    section = user[user.index("STUDENT'S DESCRIPTION:") : user.index("TECHNOLOGIES THE STUDENT CLAIMS")]
    assert "Resume says: offline habit tracker" in section and "must not be the description" not in section
