import json

import pytest

from app.schemas.api import ProjectSignals
from app.services.detectors import (
    FLAG_SEVERITY,
    DetectorHit,
    RepoSignals,
    analyse,
    compute_flags,
    compute_signals,
    depth_points,
    detect,
    detect_skills,
    is_template_readme,
    language_skills,
    matches_tutorial_name,
    parse_pom,
    parse_pyproject,
    parse_requirements,
    to_project_signals,
)
from app.services.github import GithubSnapshot, RepoData, TreeEntry


class FakeFetch:
    """Stands in for GithubSnapshot.fetcher(): serves files from a dict and records every call."""

    def __init__(self, files: dict[str, str] | None = None):
        self.files = files or {}
        self.calls: list[list[str]] = []

    def __call__(self, paths):
        self.calls.append(list(paths))
        return {p: self.files[p] for p in paths if p in self.files}

    @property
    def requested(self) -> set[str]:
        return {p for call in self.calls for p in call}


def repo(files=(), name="proj", **kw) -> RepoData:
    items = files.items() if isinstance(files, dict) else ((p, 100) for p in files)
    base = {
        "name": name,
        "url": f"https://github.com/u/{name}",
        "tree": [TreeEntry(path=p, size=s) for p, s in items],
        "detailed": True,
        "has_commit_facts": True,
        "total_commits": 20,
        "authored_commits": 15,
    }
    return RepoData(**{**base, **kw})


def skills_of(r: RepoData, fetch: FakeFetch | None = None) -> dict[str, list[DetectorHit]]:
    return detect_skills(r, fetch or FakeFetch())[0]


def kinds(hits: list[DetectorHit]) -> set[str]:
    return {h.kind for h in hits}


# ---------------------------------------------------------------- manifest parsing


def test_parse_requirements_handles_versions_extras_markers_and_noise():
    text = "fastapi==0.115\nSQLAlchemy[asyncio]>=2 ; python_version > '3.9'\n# comment\n-r other.txt\n-e .\nPyYAML_x\n"
    assert parse_requirements(text) == {"fastapi", "sqlalchemy", "pyyaml-x"}


def test_parse_pyproject_pep621_dependency_groups_and_poetry():
    pep621 = '[project]\ndependencies = ["fastapi>=0.1", "SQLAlchemy[x]"]\n[project.optional-dependencies]\nweb = ["flask"]\n[dependency-groups]\ndev = ["pytest>=8", {include-group = "x"}]\n'
    assert parse_pyproject(pep621) == {"fastapi", "sqlalchemy", "flask", "pytest"}
    poetry = '[tool.poetry.dependencies]\npython = "^3.11"\nDjango = "^5"\n[tool.poetry.group.dev.dependencies]\npytest = "*"\n'
    assert parse_pyproject(poetry) == {"django", "pytest"}
    assert parse_pyproject("not [valid toml") == set()


def test_parse_pom_reads_artifact_ids():
    assert parse_pom("<dependency><artifactId> Spring-Boot-Starter-Web </artifactId></dependency>") == {
        "spring-boot-starter-web"
    }


# ---------------------------------------------------------------- skill detectors by type


def test_npm_detector_reads_dependencies_and_dev_dependencies():
    pkg = json.dumps({"dependencies": {"react": "^18"}, "devDependencies": {"tailwindcss": "^3"}})
    found = skills_of(repo(["package.json"], manifests={"package.json": pkg}))
    assert found["react"] == [DetectorHit(kind="npm", detail="react")]
    assert "npm" in kinds(found["tailwind"])


def test_pip_detector_normalises_names_and_reads_pyproject():
    found = skills_of(
        repo(
            [],
            manifests={
                "requirements.txt": "Fast_API==1\nSQLAlchemy>=2\n",
                "pyproject.toml": '[project]\ndependencies = ["pytest"]',
            },
        )
    )
    assert "pip" in kinds(found["sql"]) and "pip" in kinds(found["pytest"])
    assert "fastapi" not in found  # "Fast_API" is not the fastapi package


def test_nested_manifests_are_fetched_in_one_call():
    fetch = FakeFetch(
        {
            "backend/requirements.txt": "flask\nredis\n",
            "frontend/package.json": json.dumps({"dependencies": {"react": "1"}}),
        }
    )
    found = skills_of(repo(["backend/requirements.txt", "frontend/package.json", "README.md"]), fetch)
    assert {"flask", "redis", "react"} <= set(found)
    assert found["flask"][0].kind == "pip"
    assert len(fetch.calls) == 1


def test_at_most_four_nested_manifests_shallowest_first():
    paths = [f"d{i}/package.json" for i in range(6)] + ["a/b/c/package.json", "requirements.txt"]
    fetch = FakeFetch()
    skills_of(repo(paths), fetch)
    manifests = [p for p in fetch.requested if p.endswith(("package.json", "requirements.txt"))]
    assert len(manifests) == 4
    assert "requirements.txt" in manifests and "a/b/c/package.json" not in manifests


def test_root_manifests_from_the_overview_are_not_fetched_again():
    fetch = FakeFetch()
    skills_of(
        repo(["package.json", "requirements.txt"], manifests={"package.json": "{}", "requirements.txt": ""}),
        fetch,
    )
    assert fetch.requested == set()
    assert fetch.calls == []


def test_maven_and_gradle_detectors():
    fetch = FakeFetch(
        {
            "pom.xml": "<artifactId>spring-boot-starter-web</artifactId>",
            "app/build.gradle": "plugins { id 'org.springframework.boot' version '3' }",
        }
    )
    assert kinds(skills_of(repo(["pom.xml"]), fetch)["spring-boot"]) == {"maven"}
    assert kinds(skills_of(repo(["app/build.gradle"]), fetch)["spring-boot"]) == {"gradle"}


def test_file_detector_matches_basenames_anywhere_and_reports_the_path():
    found = skills_of(repo(["services/api/Dockerfile", "charts/web/Chart.yaml", ".gitlab-ci.yml"]))
    assert found["docker"][0] == DetectorHit(kind="file", detail="services/api/Dockerfile")
    assert "file" in kinds(found["kubernetes"]) and "file" in kinds(found["ci-cd"])


def test_path_detector_for_directories_and_workflows():
    assert "path" in kinds(skills_of(repo(["k8s/deploy.yaml"]))["kubernetes"])
    assert "path" in kinds(skills_of(repo(["infra/k8s/svc.yaml"]))["kubernetes"])
    assert "path" in kinds(skills_of(repo([".github/workflows/ci.yml"]))["ci-cd"])
    assert "path" in kinds(skills_of(repo([], workflow_files=["ci.yml"]))["ci-cd"])
    assert "ci-cd" not in skills_of(repo(["src/k8s-notes.md", "README.md"]))


def test_extension_detector_needs_two_files_and_ignores_generated_dirs():
    assert "python" not in skills_of(repo(["main.py"]))
    two = skills_of(repo(["main.py", "util/helpers.py"]))
    assert two["python"][0].kind == "extension" and two["python"][0].detail.endswith("x2")
    vendored = [f"node_modules/pkg{i}/index.js" for i in range(5)] + ["dist/bundle.js", "static/app.min.js"]
    assert "javascript" not in skills_of(repo(vendored))


def test_content_detector_reads_at_most_five_files():
    deployment = "apiVersion: apps/v1\nkind: Deployment\n"
    fetch = FakeFetch({"deploy/app.yaml": deployment})
    assert skills_of(repo(["deploy/app.yaml"]), fetch)["kubernetes"][0] == DetectorHit(
        kind="content", detail="deploy/app.yaml"
    )
    assert "kubernetes" not in skills_of(repo(["config.yaml"]), FakeFetch({"config.yaml": "name: x\n"}))

    files = [f"a{i}.yaml" for i in range(1, 8)]  # the 6th would match, but only 5 are read
    fetch = FakeFetch({"a6.yaml": deployment})
    assert "kubernetes" not in skills_of(repo(files), fetch)
    assert {p for p in fetch.requested if p.endswith(".yaml")} == {f"a{i}.yaml" for i in range(1, 6)}


def test_content_detector_for_redis_in_compose_files():
    fetch = FakeFetch({"docker-compose.yml": "services:\n  cache:\n    image: redis:7\n"})
    assert skills_of(repo(["docker-compose.yml"]), fetch)["redis"][0].kind == "content"


def test_import_detector_matches_whole_module_names():
    fetch = FakeFetch(
        {"app/main.py": "import os\nfrom fastapi import FastAPI\n", "app/other.py": "import fastapi_users\n"}
    )
    found = skills_of(repo(["app/main.py", "app/other.py"]), fetch)
    assert found["fastapi"] == [DetectorHit(kind="import", detail="app/main.py")]
    only_lookalike = skills_of(repo(["app/other.py"]), FakeFetch({"app/other.py": "import fastapi_users\n"}))
    assert "fastapi" not in only_lookalike


def test_import_detector_reads_only_the_first_200_lines():
    inside = "x = 1\n" * 199 + "import fastapi\n"
    outside = "x = 1\n" * 200 + "import fastapi\n"
    assert "fastapi" in skills_of(repo(["main.py"]), FakeFetch({"main.py": inside}))
    assert "fastapi" not in skills_of(repo(["main.py"]), FakeFetch({"main.py": outside}))


def test_import_detector_reads_at_most_ten_files_biggest_first():
    files = {f"m{i:02d}.py": 1000 for i in range(1, 12)} | {"tiny.py": 1}
    fetch = FakeFetch({"tiny.py": "import fastapi\n"})
    assert "fastapi" not in skills_of(repo(files), fetch)
    assert len({p for p in fetch.requested if p.endswith(".py")}) == 10 and "tiny.py" not in fetch.requested


def test_test_files_are_not_chosen_for_import_scanning():
    fetch = FakeFetch()
    skills_of(repo({"tests/test_a.py": 99999, "app.py": 10}), fetch)
    assert "tests/test_a.py" not in fetch.requested and "app.py" in fetch.requested


def test_one_fetch_call_serves_manifests_content_and_imports():
    files = ["backend/requirements.txt", "k8s-app.yaml", "backend/main.py", "package.json"]
    fetch = FakeFetch({"backend/requirements.txt": "fastapi", "backend/main.py": "import fastapi"})
    skills_of(repo(files, manifests={"package.json": "{}"}), fetch)
    assert len(fetch.calls) == 1
    assert skills_of(repo([]), fetch=(empty := FakeFetch())) is not None and empty.calls == []


def test_skills_without_repository_footprint_never_fire():
    busy = repo(
        ["Dockerfile", "src/a.py", "src/b.py", "figma-export.png", "design/wireframes.pdf", "README.md"],
        readme="Figma wireframes, user research and usability testing",
        description="user research and prototyping in Figma",
    )
    found = skills_of(busy)
    for skill in (
        "figma",
        "wireframing",
        "prototyping",
        "user-research",
        "usability-testing",
        "system-design",
    ):
        assert skill not in found


def test_language_skills_from_primary_language_and_topics():
    r = repo(primary_language="Python", topics=["react", "my-own-topic"])
    assert language_skills(r) == ["python", "react"]
    assert language_skills(repo(primary_language="Jupyter Notebook")) == ["jupyter"]
    assert language_skills(repo(primary_language="Shell")) == ["bash"]
    assert language_skills(repo(primary_language="Brainfuck")) == []


# ---------------------------------------------------------------- signals


def test_signals_for_a_well_built_repo():
    files = {
        "README.md": 900,
        "LICENSE": 1000,
        "package.json": 400,
        "package-lock.json": 9999,
        "Dockerfile": 200,
        "tests/test_api.py": 500,
        "backend/app.py": 2048,
        "frontend/index.js": 1024,
        "src/utils/helpers.py": 512,
        "docs/conf.py": 300,
        "node_modules/x/index.js": 100000,
        "dist/bundle.js": 5000,
        "static/app.min.js": 3000,
        "migrations/0001_init.py": 4000,
        "assets/logo.png": 50000,
    }
    s = compute_signals(
        repo(
            files,
            description="API",
            homepage="https://demo.example.dev",
            workflow_files=["ci.yml"],
            readme="# Project\n\n## Installation\n" + "Real text. " * 40,
            authored_commits=9,
            total_commits=12,
            active_span_weeks=6.5,
        )
    )
    assert s.has_description and s.has_license and s.has_demo_url and s.has_tests and s.has_ci
    assert s.has_manifest and s.has_lockfile and s.has_deploy_config
    assert s.module_count == 3  # backend, frontend, utils (src/ stripped); tests and docs excluded
    # all authored source (tests and docs included); node_modules, dist, *.min.js, migrations, images skipped
    assert s.code_kb == pytest.approx((500 + 2048 + 1024 + 512 + 300) / 1024, abs=0.01)
    assert s.readme_substantive and s.readme_has_setup_or_screenshots and not s.readme_is_template
    assert (s.authored_commits, s.total_commits, s.authored_share, s.active_span_weeks) == (9, 12, 0.75, 6.5)


def test_signals_for_a_bare_repo():
    s = compute_signals(repo(["main.py"], total_commits=1, authored_commits=1, license=None))
    assert not any(
        [
            s.has_description,
            s.has_license,
            s.has_demo_url,
            s.has_tests,
            s.has_ci,
            s.has_manifest,
            s.has_lockfile,
        ]
    )
    assert not s.has_deploy_config and s.module_count == 0 and not s.readme_substantive
    assert (s.readme_chars, s.authored_share) == (0, 1.0)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("tests/test_a.py", True),
        ("src/__tests__/x.test.js", True),
        ("test_models.py", True),
        ("app/models_test.py", True),
        ("src/Button.spec.tsx", True),
        ("pytest.ini", True),
        ("contest.py", False),
        ("src/testimonials.js", False),
        ("latest/main.py", False),
        ("node_modules/pkg/tests/a.test.js", False),
    ],
)
def test_has_tests_rules(path, expected):
    assert compute_signals(repo([path])).has_tests is expected


@pytest.mark.parametrize(
    ("path", "ci"),
    [(".gitlab-ci.yml", True), ("Jenkinsfile", True), (".circleci/config.yml", True), ("ci-notes.md", False)],
)
def test_has_ci_from_other_ci_systems(path, ci):
    assert compute_signals(repo([path])).has_ci is ci


def test_license_file_counts_when_github_reports_none():
    assert compute_signals(repo(["LICENSE.md"], license=None)).has_license
    assert compute_signals(repo(["licenses-list.txt"], license=None)).has_license is False


def test_signals_fall_back_to_root_listing_without_a_tree():
    s = compute_signals(repo([], root_entries=["Dockerfile", "package-lock.json", "package.json"]))
    assert s.has_deploy_config and s.has_lockfile and s.has_manifest


def test_fork_signals():
    s = compute_signals(repo(["a.py"], is_fork=True, authored_since_created=0, authored_commits=7))
    assert s.is_fork and s.fork_authored_commits == 0 and s.authored_commits == 7


# ---------------------------------------------------------------- README template


CRA = (
    "# Getting Started with Create React App\n\nThis project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).\n\n"
    "## Available Scripts\n\nIn the project directory, you can run:\n\n### `npm start`\n\nRuns the app in the development mode.\n\n"
    "## Learn More\n\nYou can learn more in the Create React App documentation.\n\n### Deployment\n\nThis section has moved here.\n"
    * 2
)
NEXT = (
    "This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).\n\n"
    "## Getting Started\n\nFirst, run the development server:\n\n```bash\nnpm run dev\n```\n\n## Learn More\n\nTo learn more about Next.js, take a look at the following resources.\n\n## Deploy on Vercel\n\nThe easiest way to deploy.\n"
)
VITE = (
    "# React + Vite\n\nThis template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.\n\n"
    "Currently, two official plugins are available:\n\n- @vitejs/plugin-react uses Babel for Fast Refresh\n"
)


@pytest.mark.parametrize("readme", [CRA, NEXT, VITE], ids=["cra", "next", "vite"])
def test_starter_readmes_are_templates(readme):
    assert is_template_readme(readme)


def test_student_readme_that_kept_the_starter_heading_is_not_a_template():
    written = CRA + "\n## Features\n\n- Search flights\n- Save trips\n"
    assert not is_template_readme(written)
    assert not is_template_readme(VITE + "\n## Tech Stack\n\nReact, Express\n")


def test_other_readmes_are_not_templates():
    assert not is_template_readme("# Campus API\n\nA REST API for event registration.\n")
    assert not is_template_readme("x" * 600 + "\n# React + Vite\n")  # marker beyond the first 500 chars
    assert not is_template_readme(VITE + "filler text " * 400)  # long enough to be real work
    assert not is_template_readme("")


# ---------------------------------------------------------------- depth and flags


@pytest.mark.parametrize(
    ("commits", "weeks", "kb", "expected"),
    [(0, 0, 0, 0), (30, 4, 20, 20), (15, 2, 10, 10), (300, 40, 900, 20), (30, 0, 0, 8)],
)
def test_depth_points(commits, weeks, kb, expected):
    s = RepoSignals(authored_commits=commits, active_span_weeks=weeks, code_kb=kb)
    assert depth_points(s) == pytest.approx(expected)


def flags_for(r: RepoData, skills=None) -> dict:
    return {f.code: f for f in compute_flags(r, compute_signals(r), skills or {})}


def test_single_dump_threshold_is_three_authored_commits():
    assert "single_dump" in flags_for(repo(["a.py"], authored_commits=3, total_commits=3))
    assert "single_dump" not in flags_for(repo(["a.py"], authored_commits=4, total_commits=4))


def test_single_dump_when_first_commit_adds_80_percent_or_more():
    assert "single_dump" in flags_for(repo(["a.py"], authored_commits=10, first_commit_share=0.80))
    assert "single_dump" not in flags_for(repo(["a.py"], authored_commits=10, first_commit_share=0.79))
    assert "single_dump" not in flags_for(repo(["a.py"], authored_commits=10, first_commit_share=None))


def test_commit_flags_need_commit_facts():
    unknown = flags_for(repo(["a.py"], has_commit_facts=False, authored_commits=0, is_fork=True))
    assert "single_dump" not in unknown and "unmodified_fork" not in unknown


def test_unmodified_fork_needs_zero_own_commits_since_forking():
    untouched = flags_for(repo([], is_fork=True, authored_since_created=0, authored_commits=40))
    assert "unmodified_fork" in untouched and untouched["unmodified_fork"].severity == "high"
    assert "unmodified_fork" not in flags_for(
        repo([], is_fork=True, authored_since_created=1, authored_commits=40)
    )
    assert "unmodified_fork" not in flags_for(repo([], is_fork=False, authored_since_created=0))


def test_default_readme_flag():
    assert "default_readme" in flags_for(repo(["a.py"], readme=VITE))
    assert "default_readme" not in flags_for(repo(["a.py"], readme="# Mine\n" + "real words " * 50))
    assert "default_readme" not in flags_for(repo(["a.py"], readme=""))


@pytest.mark.parametrize(
    ("name", "description", "match"),
    [
        ("todo-app", None, True),
        ("My_Todo_App", None, True),
        ("project", "A weather app built with React", True),
        ("netflix-clone", None, True),
        ("todoist-sync-engine", None, False),
        ("weatherstation", "IoT firmware", False),
        ("campus-api", "Event registration API", False),
    ],
)
def test_tutorial_name_matching_uses_whole_words(name, description, match):
    assert matches_tutorial_name(repo(name=name, description=description)) is match


def test_tutorial_pattern_needs_a_shallow_history():
    deep = repo(["a.py"], name="todo-app", authored_commits=30, active_span_weeks=0, code_kb=0)
    shallow = repo(["a.py"], name="todo-app", authored_commits=29, active_span_weeks=0, code_kb=0)
    assert "tutorial_pattern" not in flags_for(deep)  # depth exactly 8.0
    assert "tutorial_pattern" in flags_for(shallow)  # depth 7.73
    assert "tutorial_pattern" not in flags_for(repo(["a.py"], name="campus-api", authored_commits=2))


LLM_HIT = {"llm-apis": [DetectorHit(kind="pip", detail="openai")]}


def wrapper(kb: float, **kw) -> RepoData:
    return repo({"app.py": int(kb * 1024)}, description=kw.pop("description", "An autonomous AI agent"), **kw)


def test_thin_wrapper_needs_llm_dependency_small_code_and_a_big_claim():
    assert "thin_wrapper" in flags_for(wrapper(11.9), LLM_HIT)
    assert "thin_wrapper" not in flags_for(wrapper(12.0), LLM_HIT)  # large enough
    assert "thin_wrapper" not in flags_for(wrapper(5), {})  # no LLM SDK
    assert "thin_wrapper" not in flags_for(wrapper(5, description="Summarises meeting notes"), LLM_HIT)
    in_readme = wrapper(5, description="notes helper", readme="# Notes\nAn agentic system that plans tasks.")
    assert "thin_wrapper" in flags_for(in_readme, LLM_HIT)
    assert "thin_wrapper" not in flags_for(wrapper(5), {"llm-apis": [DetectorHit(kind="file", detail="x")]})


def test_severity_follows_the_fixed_map():
    assert FLAG_SEVERITY == {
        "unmodified_fork": "high",
        "single_dump": "medium",
        "default_readme": "medium",
        "thin_wrapper": "medium",
        "tutorial_pattern": "low",
    }


def test_flag_wording_never_accuses_or_claims_ai_detection():
    banned = (
        "slop",
        "fake",
        "larp",
        "dishonest",
        "cheat",
        "copied",
        "plagiar",
        "ai-generated",
        "written by ai",
    )
    common = {"name": "todo-app", "readme": VITE, "description": "autonomous ai agent"}
    own = repo({"app.py": 1024}, authored_commits=1, **common)
    fork = repo({"app.py": 1024}, is_fork=True, authored_since_created=0, authored_commits=1, **common)
    found = compute_flags(own, compute_signals(own), LLM_HIT) + compute_flags(
        fork, compute_signals(fork), LLM_HIT
    )
    assert {f.code for f in found} == set(FLAG_SEVERITY)
    for f in found:
        text = f"{f.reason} {f.fix}".lower()
        assert not any(word in text for word in banned), f.code
        assert f.reason and f.fix


def test_an_untouched_fork_gets_the_fork_flag_only_not_also_single_dump():
    untouched = flags_for(repo([], is_fork=True, authored_since_created=0, authored_commits=0))
    assert set(untouched) == {"unmodified_fork"}
    one_commit = flags_for(repo([], is_fork=True, authored_since_created=1, authored_commits=1))
    assert set(one_commit) == {"single_dump"}


def test_type_declaration_files_do_not_count_as_code():
    s = compute_signals(repo({"src/app.ts": 2048, "types/schema.d.ts": 99999}))
    assert s.code_kb == pytest.approx(2.0, abs=0.01)


# ---------------------------------------------------------------- entry points


def test_to_project_signals_maps_the_contract_fields():
    s = RepoSignals(
        has_tests=True,
        has_ci=False,
        has_demo_url=True,
        has_license=True,
        readme_substantive=True,
        has_deploy_config=False,
        authored_commits=9,
        total_commits=12,
    )
    assert to_project_signals(s) == ProjectSignals(
        tests=True, ci=False, demo_url=True, license=True, readme=True, deploy_config=False,
        authored_commits=9, total_commits=12,
    )  # fmt: skip


def test_detect_combines_skills_signals_and_flags():
    fetch = FakeFetch({"requirements.txt": "fastapi\npytest\n"})
    r = repo(["requirements.txt", "tests/test_a.py", "app/main.py", "app/db.py"], primary_language="Python")
    result = detect(r, fetch)
    assert {"fastapi", "pytest", "python"} <= set(result.skills) | set(result.language_skills)
    assert result.signals.has_tests and result.repo_name == "proj" and result.flags == []


def test_analyse_covers_detailed_repos_and_forks_with_facts_only():
    snapshot = GithubSnapshot(
        login="u",
        user_id="X",
        repos=[
            repo(["a.py", "b.py"], name="mine"),
            repo([], name="forked", detailed=False, is_fork=True, authored_since_created=0),
            RepoData(name="old", url="https://github.com/u/old"),  # outside the top 8: no tree, no facts
        ],
    )
    result = analyse(snapshot)
    assert set(result) == {"mine", "forked"}
    assert "unmodified_fork" in {f.code for f in result["forked"].flags}
    assert snapshot.fetcher("mine")(["x"]) == {}  # no client bound: nothing to fetch
