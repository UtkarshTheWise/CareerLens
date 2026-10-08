import pytest

from app.db import models
from app.db.base import SessionLocal
from app.errors import ApiError
from app.schemas.api import QuizCreate
from app.schemas.llm import GeneratedQuestion
from app.services import quiz
from app.services.portfolio import PageText
from app.services.quiz import Slot, create_quiz, mix_for, pick, validate_question
from app.services.quiz_context import QuizContext
from tests.llm_fakes import SchemaProvider
from tests.quiz_helpers import (
    FILES,
    T0,
    FakeGitHub,
    deps,
    full_verify_reply,
    inputs_with_repo,
    make_analysis,
    mcq,
    short,
)
from tests.scoring_helpers import design_project
from tests.scoring_helpers import inputs as bare_inputs


def ctx(kind: str = "code") -> QuizContext:
    if kind == "design":
        return QuizContext(
            kind="design",
            title="Transit",
            url="https://x.dev/case",
            page_text="Problem\nResearch with five riders",
        )
    files = {
        "main.py": [f"line {i}" for i in range(1, 61)],
        "app/db.py": [f"db {i}" for i in range(1, 81)],
        "app/routes.py": [f"route {i}" for i in range(1, 121)],
    }
    return QuizContext(kind="code", title="p", url="https://github.com/u/p", files=files)


def question(**kw) -> GeneratedQuestion:
    return GeneratedQuestion.model_validate({**short("architecture"), **kw})


# ---------------------------------------------------------------- the mix


def test_verify_code_mix_is_two_mcq_and_four_short_answers():
    slots = mix_for("verify", "code")
    assert len(slots) == 6 and sum(s.type == "mcq" for s in slots) == 2
    assert {c for s in slots for c in s.categories} == {
        "code_reading", "architecture", "design_decision", "debugging", "extension", "claim_check",
    }  # fmt: skip


def test_verify_design_mix_has_no_mcq():
    slots = mix_for("verify", "design")
    assert len(slots) == 6 and all(s.type == "short_answer" for s in slots)
    assert {c for s in slots for c in s.categories} == {"process", "design_decision", "outcome", "critique"}


@pytest.mark.parametrize("count", range(3, 11))
def test_practice_mix_never_exceeds_a_third_mcq(count):
    slots = mix_for("practice", "code", count)
    assert len(slots) == count
    assert 1 <= sum(s.type == "mcq" for s in slots) <= max(1, count // 3)
    assert all(s.type == "short_answer" for s in mix_for("practice", "design", count))


def test_pick_prefers_the_exact_category_then_falls_back_to_the_type():
    slots = [Slot(("debugging",), "short_answer"), Slot(("architecture",), "short_answer")]
    chosen, missing = pick([question(category="architecture"), question(category="extension")], slots)
    assert (chosen[0].category, chosen[1].category, missing) == ("extension", "architecture", 0)
    chosen, missing = pick([question(category="architecture")], slots)
    assert chosen[0] is None and missing == 1
    assert pick([mcq_question()], slots)[1] == 2  # an MCQ never fills a short-answer slot


def mcq_question(**kw) -> GeneratedQuestion:
    return GeneratedQuestion.model_validate({**mcq(), **kw})


# ---------------------------------------------------------------- validation


def test_a_good_question_passes_and_unknown_skills_are_dropped():
    out = validate_question(question(skill_ids=["python", "no-such-skill", "python"]), ctx())
    assert out is not None and out.skill_ids == ["python"]


@pytest.mark.parametrize(
    "change",
    [
        {"source_ref": {"path": "ghost.py", "start_line": 1, "end_line": 5}},  # file not in the material
        {"source_ref": {"path": "main.py", "start_line": 50, "end_line": 70}},  # past the end
        {"source_ref": {"path": "main.py", "start_line": 9, "end_line": 3}},
        {"source_ref": {"path": "main.py"}},  # no lines
        {"source_ref": None},
        {"prompt": "Too short"},
        {"model_answer": ""},
        {"key_points": ["only one", "and two"]},
    ],
)
def test_questions_citing_things_that_do_not_exist_are_dropped(change):
    assert validate_question(question(**change), ctx()) is None


def test_claim_check_needs_no_source_ref():
    q = question(
        category="claim_check", source_ref=None, prompt="Your description mentions Redis. Where is it used?"
    )
    assert validate_question(q, ctx()) is not None


@pytest.mark.parametrize(
    "change",
    [
        {"correct_choice_id": "z"},
        {"correct_choice_id": None},
        {"options": mcq()["options"][:3]},
        {
            "options": [
                {"id": "a", "text": "x"},
                {"id": "a", "text": "y"},
                {"id": "c", "text": "z"},
                {"id": "d", "text": "w"},
            ]
        },
        {"options": [{"id": i, "text": "same"} for i in "abcd"]},
    ],
)
def test_malformed_mcq_is_dropped(change):
    assert validate_question(mcq_question(**change), ctx()) is None


def test_key_points_are_capped_at_five():
    out = validate_question(question(key_points=[f"point number {i}" for i in range(8)]), ctx())
    assert len(out.key_points) == 5


def test_design_questions_cite_a_section_of_the_page_and_never_mcq():
    c = ctx("design")
    good = question(
        category="process", source_ref={"path": "whatever", "section": "Research with five riders"}
    )
    out = validate_question(good, c)
    assert out is not None and out.source_ref.path == "https://x.dev/case"  # normalised to the page URL
    assert (
        validate_question(question(category="process", source_ref={"path": "x", "section": "Made up"}), c)
        is None
    )
    assert validate_question(mcq_question(), c) is None


# ---------------------------------------------------------------- generation with a scripted model


def run_generate(provider: SchemaProvider, mode: str = "verify", kind: str = "code"):
    with SessionLocal() as db:
        return quiz.generate_questions(ctx(kind), mix_for(mode, kind), mode, 1, db, [provider])


def test_generation_makes_one_call_when_the_mix_is_complete(client):
    provider = SchemaProvider({"GeneratedQuiz": full_verify_reply()})
    questions = run_generate(provider)
    assert [q.type for q in questions].count("mcq") == 2 and len(questions) == 6
    assert len(provider.calls_for("GeneratedQuiz")) == 1


def test_generation_asks_once_more_for_missing_categories(client):
    reply = full_verify_reply()
    first = {"questions": [q for q in reply["questions"] if q["category"] != "debugging"]}
    extra = {
        "questions": [short("debugging", prompt="Two requests hit the same row. What goes wrong first?")]
    }

    def respond(user: str):
        return extra if "REPLACEMENTS" in user else first

    provider = SchemaProvider({"GeneratedQuiz": respond})
    questions = run_generate(provider)
    assert len(questions) == 6 and "debugging" in [q.category for q in questions]
    assert len(provider.calls_for("GeneratedQuiz")) == 2
    assert "debugging" in provider.calls_for("GeneratedQuiz")[1]["user"]


def test_invalid_questions_trigger_the_replacement_round_and_are_replaced(client):
    bad = full_verify_reply()
    bad["questions"][2]["source_ref"] = {"path": "ghost.py", "start_line": 1, "end_line": 4}
    good = {"questions": [short("architecture", prompt="Trace a request from the route to the database.")]}
    provider = SchemaProvider({"GeneratedQuiz": lambda user: good if "REPLACEMENTS" in user else bad})
    questions = run_generate(provider)
    assert len(questions) == 6 and all(
        q.source_ref is None or q.source_ref.path != "ghost.py" for q in questions
    )


def test_too_few_usable_questions_is_a_clear_502(client):
    only_two = {"questions": full_verify_reply()["questions"][:2]}
    with pytest.raises(ApiError) as caught:
        run_generate(SchemaProvider({"GeneratedQuiz": only_two}))
    assert caught.value.status_code == 502 and caught.value.code == "quiz_generation_failed"


def test_a_failed_replacement_round_still_returns_what_is_usable(client):
    reply = full_verify_reply()
    reply["questions"] = reply["questions"][:5]  # extension missing; 5 >= the minimum of 4
    provider = SchemaProvider(
        {"GeneratedQuiz": lambda user: {"questions": []} if "REPLACEMENTS" in user else reply}
    )
    assert len(run_generate(provider)) == 5


def test_repeated_prompts_in_the_replacement_round_are_ignored(client):
    reply = full_verify_reply()
    first = {"questions": reply["questions"][:5]}
    dup = {"questions": [reply["questions"][2]]}  # same prompt as one we already have
    provider = SchemaProvider({"GeneratedQuiz": lambda user: dup if "REPLACEMENTS" in user else first})
    assert len(run_generate(provider)) == 5


# ---------------------------------------------------------------- stored questions


def test_create_quiz_stores_questions_with_snippets_limits_and_keys(client):
    provider = SchemaProvider({"GeneratedQuiz": full_verify_reply()})
    with SessionLocal() as db:
        analysis = make_analysis(db)
        body = QuizCreate(project_id="proj-campus-api", mode="verify")
        made = create_quiz(db, analysis, body, deps(provider), now=T0)
        rows = list(made.questions)
        assert made.mode == "verify" and made.status == "in_progress" and made.attempt == 1
        assert made.project_title == "campus-api" and made.created_at == T0
        assert [r.order for r in rows] == [1, 2, 3, 4, 5, 6]
        first, shorty = rows[0], rows[2]
        assert first.type == "mcq" and [o["id"] for o in first.options] == ["a", "b", "c", "d"]
        correct = next(o for o in first.options if o["id"] == first.correct_choice_id)
        assert correct["text"] == "It returns an empty list"  # the key follows the shuffled option
        assert (first.time_limit_s, shorty.time_limit_s) == (60, 180)
        assert first.code_snippet["path"] == "main.py" and first.code_snippet["language"] == "python"
        assert first.code_snippet["start_line"] == 3 and first.code_snippet["end_line"] == 12
        assert first.code_snippet["code"].splitlines()[0] == "# main.py line 3"
        assert first.source_ref["url"] == "https://github.com/u/campus-api/blob/HEAD/main.py#L3-L12"
        assert shorty.key_points and shorty.model_answer and shorty.correct_choice_id is None
        assert (
            shorty.code_snippet is None
            or shorty.code_snippet["end_line"] - shorty.code_snippet["start_line"] < 30
        )


def test_second_attempt_numbers_and_prompt_say_so(client):
    provider = SchemaProvider({"GeneratedQuiz": full_verify_reply()})
    with SessionLocal() as db:
        analysis = make_analysis(db)
        body = QuizCreate(project_id="proj-campus-api", mode="practice", question_count=6)
        create_quiz(db, analysis, body, deps(provider), now=T0)
        second = create_quiz(db, analysis, body, deps(provider), now=T0)
    assert second.attempt == 2 and "ATTEMPT: 2" in provider.calls_for("GeneratedQuiz")[-1]["user"]


def test_practice_questions_have_no_time_limit(client):
    provider = SchemaProvider({"GeneratedQuiz": full_verify_reply()})
    with SessionLocal() as db:
        made = create_quiz(
            db,
            make_analysis(db),
            QuizCreate(project_id="proj-campus-api", mode="practice"),
            deps(provider),
            now=T0,
        )
        assert all(r.time_limit_s is None for r in made.questions)


def test_the_prompt_carries_the_students_files_and_never_pii(client):
    provider = SchemaProvider({"GeneratedQuiz": full_verify_reply()})
    with SessionLocal() as db:
        create_quiz(
            db,
            make_analysis(db),
            QuizCreate(project_id="proj-campus-api", mode="verify"),
            deps(provider),
            now=T0,
        )
    user = provider.calls_for("GeneratedQuiz")[0]["user"]
    assert "FILE main.py" in user and "   3| # main.py line 3" in user and "campus-api" in user


# ---------------------------------------------------------------- refusing to quiz


def test_unknown_project_and_unfinished_analysis(client):
    provider = SchemaProvider({"GeneratedQuiz": full_verify_reply()})
    with SessionLocal() as db:
        analysis = make_analysis(db)
        with pytest.raises(ApiError) as missing:
            create_quiz(
                db, analysis, QuizCreate(project_id="proj-ghost", mode="verify"), deps(provider), now=T0
            )
        assert missing.value.status_code == 404
        running = make_analysis(db, status="judging")
        with pytest.raises(ApiError) as busy:
            create_quiz(
                db, running, QuizCreate(project_id="proj-campus-api", mode="verify"), deps(provider), now=T0
            )
        assert busy.value.status_code == 409 and busy.value.code == "analysis_not_ready"


def test_untouched_forks_and_urlless_projects_are_not_quizzable(client):
    from tests.scoring_helpers import code_project, sig

    fork = code_project("forked", signals=sig(is_fork=True, fork_authored_commits=0))
    local = code_project("local-only").model_copy(update={"url": None})
    inputs = bare_inputs(projects=[fork, local])
    provider = SchemaProvider({"GeneratedQuiz": full_verify_reply()})
    with SessionLocal() as db:
        analysis = make_analysis(db, inputs)
        for pid in ("proj-forked", "proj-local-only"):
            with pytest.raises(ApiError) as caught:
                create_quiz(db, analysis, QuizCreate(project_id=pid, mode="verify"), deps(provider), now=T0)
            assert caught.value.status_code == 422 and caught.value.code == "project_not_quizzable"
    assert provider.calls == []


def test_no_readable_source_files_is_a_502(client):
    provider = SchemaProvider({"GeneratedQuiz": full_verify_reply()})
    with SessionLocal() as db:
        analysis = make_analysis(db)
        with pytest.raises(ApiError) as caught:
            create_quiz(
                db, analysis, QuizCreate(project_id="proj-campus-api", mode="verify"),
                deps(provider, FakeGitHub({"logo.png": ""})), now=T0,
            )  # fmt: skip
        assert caught.value.status_code == 502 and caught.value.code == "quiz_context_unavailable"


def test_github_trouble_is_a_502_not_a_crash(client):
    class Down(FakeGitHub):
        def rest_get(self, path, *, missing_ok=False):
            raise ApiError(502, "github_unavailable", "down")

    provider = SchemaProvider({"GeneratedQuiz": full_verify_reply()})
    with SessionLocal() as db:
        with pytest.raises(ApiError) as caught:
            create_quiz(
                db, make_analysis(db), QuizCreate(project_id="proj-campus-api", mode="verify"),
                deps(provider, Down()), now=T0,
            )  # fmt: skip
        assert caught.value.status_code == 502 and caught.value.code == "quiz_context_unavailable"


def test_llm_trouble_maps_to_the_contract_status_codes(client):
    from app.services.llm import ProviderUnavailable

    body = QuizCreate(project_id="proj-campus-api", mode="verify")
    with SessionLocal() as db:
        analysis = make_analysis(db)
        down = SchemaProvider({"GeneratedQuiz": ProviderUnavailable("busy")})
        with pytest.raises(ApiError) as busy:
            create_quiz(db, analysis, body, deps(down), now=T0)
        assert busy.value.status_code == 429 and busy.value.code == "llm_unavailable"
        none = deps(SchemaProvider({}))
        none.providers = []
        with pytest.raises(ApiError) as unset:
            create_quiz(db, analysis, body, none, now=T0)
        assert unset.value.status_code == 503


def test_a_design_project_is_quizzed_from_the_page(client):
    from app.services.scoring_inputs import DesignInput

    project = design_project(
        "Transit app case study", design=DesignInput(problem_statement=20, process_evidence=20)
    )
    page = PageText(
        url=project.url, readable=True, text="Problem\nRiders cannot find stops\nResearch interviews"
    )
    reply = {
        "questions": [
            short("process", prompt="How did your research shape the first design?",
                  source_ref={"path": project.url, "section": "Research interviews"}),
            short("design_decision", prompt="Why did you choose that layout for finding stops?",
                  source_ref={"path": project.url, "section": "Riders cannot find stops"}),
            short("outcome", prompt="What changed after you tested it with riders?",
                  source_ref={"path": project.url, "section": "Problem"}),
            short("critique", prompt="What would you change for accessibility?",
                  source_ref={"path": project.url, "section": "Research interviews"}),
        ]
    }  # fmt: skip
    provider = SchemaProvider({"GeneratedQuiz": reply})
    pipeline_deps = deps(provider)
    pipeline_deps.fetch_page = lambda url, db, fresh: page
    inputs = bare_inputs(projects=[project])
    with SessionLocal() as db:
        analysis = make_analysis(db, inputs)
        made = create_quiz(
            db, analysis, QuizCreate(project_id=project.project_id, mode="verify"), pipeline_deps, now=T0
        )
        assert made.kind == "design" and len(made.questions) == 4
        assert all(q.code_snippet is None and q.source_ref["url"] == project.url for q in made.questions)
        assert all(q.type == "short_answer" and q.time_limit_s == 180 for q in made.questions)
        assert db.query(models.Quiz).count() == 1


def test_fixture_files_are_what_the_helpers_say():
    assert "main.py" in FILES and inputs_with_repo().projects[0].project_id == "proj-campus-api"
