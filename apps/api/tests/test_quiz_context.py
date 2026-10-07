from app.services.detectors import DetectorHit
from app.services.github import TreeEntry
from app.services.portfolio import PageText
from app.services.quiz_context import (
    MAX_FILE_CHARS,
    MAX_FILES,
    MAX_TOTAL_CHARS,
    README_CHARS,
    build_code_context,
    build_design_context,
    repo_from_url,
    select_files,
)
from tests.scoring_helpers import code_project, design_project


def tree(sizes: dict[str, int]) -> list[TreeEntry]:
    return [TreeEntry(path=p, size=n) for p, n in sizes.items()]


def test_repo_from_url():
    assert repo_from_url("https://github.com/u/campus-api") == ("u", "campus-api")
    assert repo_from_url("https://github.com/u/campus-api.git/") == ("u", "campus-api")
    assert repo_from_url("https://example.com/u/x") is None and repo_from_url(None) is None


def test_select_prefers_entry_points_then_detector_files_then_largest():
    project = code_project("campus-api", skills=["python"], claimed_skill_ids=["sql"])
    project.skills["sql"] = [DetectorHit(kind="file", detail="app/db.py")]
    entries = tree(
        {"main.py": 300, "app/db.py": 900, "app/routes.py": 4000, "app/utils.py": 2500, "Dockerfile": 100,
         "big.py": 9000}
    )  # fmt: skip
    # entry point, then the file a claimed skill's detector fired on, then the largest source files
    assert select_files(entries, project) == [
        "main.py",
        "app/db.py",
        "big.py",
        "app/routes.py",
        "app/utils.py",
    ]


def test_select_skips_generated_vendored_minified_and_test_files():
    entries = tree(
        {"main.py": 100, "package-lock.json": 90000, "node_modules/lib/index.js": 50000,
         "dist/bundle.js": 40000, "migrations/001_init.py": 30000, "vendor/x.py": 20000,
         "static/app.min.js": 10000, "tests/test_main.py": 8000, "src/utils.spec.ts": 7000,
         "app/core.py": 500}
    )  # fmt: skip
    chosen = select_files(entries, code_project("p"))
    assert set(chosen) == {"main.py", "app/core.py"}


def test_select_ignores_hits_outside_the_tree_and_non_file_hits():
    project = code_project("campus-api", skills=["python"])
    project.skills["python"] = [
        DetectorHit(kind="pip", detail="fastapi"),
        DetectorHit(kind="file", detail="gone.py"),
    ]
    assert select_files(tree({"main.py": 10}), project) == ["main.py"]


def test_select_never_returns_more_than_five():
    entries = tree({f"module{i}.py": 1000 + i for i in range(20)})
    assert len(select_files(entries, code_project("p"))) == MAX_FILES


def test_build_code_context_caps_each_file_and_the_total():
    texts = {f"f{i}.py": "\n".join(f"x{j} = {j}" for j in range(3000)) for i in range(5)}
    texts["README.md"] = "r" * 5000
    entries = [TreeEntry(path=p, size=len(t)) for p, t in texts.items()]
    ctx = build_code_context(
        code_project("p"), entries, lambda paths: {p: texts[p] for p in paths if p in texts}
    )
    sizes = [sum(len(line) + 1 for line in lines) for lines in ctx.files.values()]
    assert all(s <= MAX_FILE_CHARS for s in sizes) and sum(sizes) <= MAX_TOTAL_CHARS
    assert len(ctx.readme) == README_CHARS


def test_context_numbers_lines_and_validates_ranges():
    entries = tree({"main.py": 40})
    ctx = build_code_context(code_project("p"), entries, lambda paths: {"main.py": "a\nb\nc"})
    assert ctx.numbered("main.py") == "   1| a\n   2| b\n   3| c"
    assert ctx.has_range("main.py", 1, 3) and ctx.has_range("main.py", 2, 2)
    assert not ctx.has_range("main.py", 0, 2) and not ctx.has_range("main.py", 2, 4)
    assert not ctx.has_range("main.py", 3, 2) and not ctx.has_range("other.py", 1, 1)
    assert not ctx.has_range("main.py", None, None)
    assert ctx.blob_url("main.py", 1, 3) == "https://github.com/u/p/blob/HEAD/main.py#L1-L3"
    assert ctx.excerpt("main.py", 2, 3) == "b\nc"


def test_empty_and_missing_files_are_left_out():
    entries = tree({"main.py": 10, "app.py": 10})
    ctx = build_code_context(code_project("p"), entries, lambda paths: {"main.py": "  \n", "app.py": "x = 1"})
    assert list(ctx.files) == ["app.py"]


def test_skill_names_come_from_the_catalogue():
    ctx = build_code_context(
        code_project("p", skills=["python"], claimed_skill_ids=["sql", "not-a-skill"]),
        tree({"a.py": 5}),
        lambda p: {},
    )
    assert ctx.claimed == {"sql": "SQL"} and ctx.detected == {"python": "Python"}


def test_design_context_uses_the_page_text_and_section_matching():
    page = PageText(
        url="https://x.dev/case", readable=True, text="Problem\nUsers  struggle   to find buses.\nResearch"
    )
    ctx = build_design_context(design_project("Transit"), page, description="My case study")
    assert ctx.kind == "design" and ctx.files == {} and ctx.description == "My case study"
    assert ctx.has_section("users struggle to find buses") and ctx.has_section("Research")
    assert (
        not ctx.has_section("something else entirely")
        and not ctx.has_section("")
        and not ctx.has_section("ab")
    )
    assert "CASE STUDY PAGE" in ctx.prompt_material()


def test_unreadable_design_page_gives_no_text():
    ctx = build_design_context(design_project("Transit"), PageText(url="u", readable=False, reason="blocked"))
    assert ctx.page_text == ""
