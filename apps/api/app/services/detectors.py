"""Stage 4 (docs/PIPELINE.md): skill detectors, repo quality signals and rule flags. No LLM.

Pure functions over a `RepoData` snapshot (docs/SCORING.md §2B, §4, §5). The only I/O is the
injected `fetch` callable, used once per repo to read manifests and the few files that the
`content` and `imports` detectors need. B5 (scoring) consumes `RepoSignals`; B6 consumes the flags.
"""

import fnmatch
import json
import re
import tomllib
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, Field

from app import catalogue
from app.catalogue import SkillDef
from app.schemas.api import ProjectSignals
from app.services.github import FileFetcher, GithubSnapshot, RepoData

# ---------------------------------------------------------------- limits (docs/SCORING.md §4)

EXTENSION_MIN_FILES = 2  # one stray .py file is not evidence of Python
CONTENT_MAX_FILES = 5  # files read per `content` detector
IMPORT_MAX_FILES = 10  # source files read per language for `imports`
IMPORT_MAX_LINES = 200
NESTED_MANIFEST_MAX = 4
THIN_WRAPPER_MAX_KB = 12.0  # about 300 lines
README_SUBSTANTIVE_CHARS = 300
TEMPLATE_README_MAX_CHARS = 4000

# ---------------------------------------------------------------- file classification

GENERATED_DIRS = {
    "node_modules", "dist", "build", ".next", ".nuxt", "vendor", "target", "__pycache__", ".venv", "venv",
    "env", ".git", "coverage", "out", ".cache", "migrations", "site-packages", "bower_components", ".gradle",
    ".idea", ".vscode", "staticfiles", ".dart_tool", "pods",
}  # fmt: skip
LOCKFILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock", "pipfile.lock",
    "composer.lock", "cargo.lock", "go.sum", "gemfile.lock", "gradle.lockfile", "bun.lockb",
}  # fmt: skip
SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".java", ".kt",
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".go", ".rs", ".rb", ".php", ".cs", ".swift", ".dart",
    ".vue", ".svelte", ".html", ".css", ".scss", ".sass", ".sql", ".sh", ".bash",
}  # fmt: skip
MANIFEST_NAMES = {
    "package.json", "pyproject.toml", "pom.xml", "build.gradle", "build.gradle.kts", "go.mod", "cargo.toml",
    "pipfile", "composer.json", "gemfile",
}  # fmt: skip
TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs", "e2e", "cypress", "testing"}
TEST_FILE = re.compile(
    r"(?:^test_.*\.py$|.*_test\.(?:py|go)$|.*\.(?:test|spec)\.(?:js|jsx|ts|tsx|mjs)$|.*Tests?\.java$)"
)
TEST_CONFIG_FILES = {
    "pytest.ini",
    "conftest.py",
    "jest.config.js",
    "jest.config.ts",
    "vitest.config.ts",
    "vitest.config.js",
}
CI_FILES = {".gitlab-ci.yml", "jenkinsfile", ".travis.yml", "azure-pipelines.yml", "bitbucket-pipelines.yml"}
DEPLOY_FILES = {
    "dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml", "vercel.json",
    "netlify.toml", "procfile", "render.yaml", "fly.toml", "railway.json", "railway.toml", "app.yaml",
    "serverless.yml", "serverless.yaml", "heroku.yml", "cloudbuild.yaml", "buildspec.yml", "firebase.json",
    "wrangler.toml", "chart.yaml", "now.json",
}  # fmt: skip
MODULE_ROOTS = {"src", "app", "lib", "source", "packages"}
NON_MODULE_DIRS = TEST_DIRS | {"docs", "doc", "scripts", "script", "config", "configs", "examples", "assets"}
LANG_EXTENSIONS = {
    "python": (".py",),
    "javascript": (".js", ".jsx", ".mjs", ".cjs"),
    "typescript": (".ts", ".tsx"),
    "java": (".java",),
}


def _parts(path: str) -> list[str]:
    return path.split("/")


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _ext(path: str) -> str:
    base = _basename(path)
    return base[base.rfind(".") :].lower() if "." in base else ""


def is_generated(path: str) -> bool:
    parts = _parts(path)
    base = parts[-1].lower()
    return (
        any(p.lower() in GENERATED_DIRS for p in parts[:-1])
        or base in LOCKFILES
        or ".min." in base
        or base.endswith((".map", ".lock", ".pb.go", ".d.ts"))  # .d.ts: type declarations, usually generated
        or ".generated." in base
    )


def _is_source(path: str) -> bool:
    return _ext(path) in SOURCE_EXTENSIONS and not is_generated(path)


def _is_test_path(path: str) -> bool:
    parts = _parts(path)
    return any(p.lower() in TEST_DIRS for p in parts[:-1]) or bool(TEST_FILE.match(parts[-1]))


# ---------------------------------------------------------------- output models


class DetectorHit(BaseModel):
    kind: Literal["npm", "pip", "maven", "gradle", "file", "path", "extension", "content", "import"]
    detail: str  # the package, file or pattern that fired: used to link evidence in the report


class RepoSignals(BaseModel):
    """Facts SCORING.md §2B scores, plus the commit facts. All derived, nothing subjective."""

    readme_chars: int = 0
    readme_is_template: bool = False
    readme_substantive: bool = False  # > 300 chars and not a starter template
    readme_has_setup_or_screenshots: bool = False
    has_description: bool = False
    has_license: bool = False
    has_demo_url: bool = False
    has_tests: bool = False
    has_ci: bool = False
    has_manifest: bool = False
    has_lockfile: bool = False
    module_count: int = 0
    has_deploy_config: bool = False
    commit_facts_known: bool = False
    authored_commits: int = 0
    total_commits: int = 0
    authored_share: float = 0.0
    is_fork: bool = False
    fork_authored_commits: int = 0  # authored commits since the fork was created
    active_span_weeks: float = 0.0
    code_kb: float = 0.0  # non-generated source code
    first_commit_share: float | None = None


FlagCode = Literal["single_dump", "unmodified_fork", "default_readme", "tutorial_pattern", "thin_wrapper"]


class RuleFlag(BaseModel):
    """A low-evidence flag. Describes what is missing, never who wrote anything."""

    code: FlagCode
    severity: Literal["low", "medium", "high"]
    reason: str
    fix: str


class RepoAnalysis(BaseModel):
    repo_name: str
    skills: dict[str, list[DetectorHit]] = Field(default_factory=dict)  # skill_id -> hits
    language_skills: list[str] = Field(default_factory=list)  # primary language / topic matches
    signals: RepoSignals
    flags: list[RuleFlag] = Field(default_factory=list)


# Decision N4 (Phase 0): one fixed severity per flag code.
FLAG_SEVERITY: dict[str, Literal["low", "medium", "high"]] = {
    "unmodified_fork": "high",
    "single_dump": "medium",
    "default_readme": "medium",
    "thin_wrapper": "medium",
    "tutorial_pattern": "low",
}


# ---------------------------------------------------------------- manifests


def _norm_pkg(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def _pep508_name(spec: str) -> str | None:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", spec)
    return _norm_pkg(match.group(1)) if match else None


def parse_requirements(text: str) -> set[str]:
    names = set()
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "git+", "http")):
            continue
        if name := _pep508_name(line.split(";", 1)[0]):
            names.add(name)
    return names


def parse_pyproject(text: str) -> set[str]:
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return set()
    names: set[str] = set()

    def specs(items: object) -> None:
        for item in items if isinstance(items, list) else []:
            if isinstance(item, str) and (name := _pep508_name(item)):
                names.add(name)

    project = doc.get("project", {})
    specs(project.get("dependencies"))
    for group in project.get("optional-dependencies", {}).values():
        specs(group)
    for group in doc.get("dependency-groups", {}).values():
        specs(group)
    poetry = doc.get("tool", {}).get("poetry", {})
    for table in (poetry.get("dependencies"), poetry.get("dev-dependencies")):
        names.update(_norm_pkg(k) for k in (table or {}) if k.lower() != "python")
    for group in poetry.get("group", {}).values():
        names.update(_norm_pkg(k) for k in group.get("dependencies", {}))
    return names


def parse_package_json(text: str) -> set[str]:
    try:
        doc = json.loads(text)
    except ValueError:
        return set()
    if not isinstance(doc, dict):
        return set()
    names: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        if isinstance(doc.get(key), dict):
            names.update(k.lower() for k in doc[key])
    return names


def parse_pom(text: str) -> set[str]:
    return {m.lower() for m in re.findall(r"<artifactId>\s*([^<\s]+)\s*</artifactId>", text)}


class _Deps(BaseModel):
    npm: set[str] = Field(default_factory=set)
    pip: set[str] = Field(default_factory=set)
    maven: set[str] = Field(default_factory=set)
    gradle_text: str = ""


def _add_manifest(deps: _Deps, path: str, text: str) -> None:
    base = _basename(path).lower()
    if base == "package.json":
        deps.npm |= parse_package_json(text)
    elif base == "pyproject.toml":
        deps.pip |= parse_pyproject(text)
    elif base.startswith("requirements") and base.endswith(".txt"):
        deps.pip |= parse_requirements(text)
    elif base == "pom.xml":
        deps.maven |= parse_pom(text)
    elif base in ("build.gradle", "build.gradle.kts"):
        deps.gradle_text += "\n" + text.lower()


def _is_manifest_file(path: str) -> bool:
    base = _basename(path).lower()
    return base in MANIFEST_NAMES or (base.startswith("requirements") and base.endswith(".txt"))


# ---------------------------------------------------------------- file selection


def _repo_paths(repo: RepoData) -> list[str]:
    """Paths of all files; falls back to the root listing if the tree could not be read."""
    return [e.path for e in repo.tree] if repo.tree else list(repo.root_entries)


def _import_regex(lang: str, modules: Sequence[str]) -> re.Pattern[str]:
    alts = "|".join(re.escape(m) for m in modules)
    if lang == "python":
        return re.compile(rf"^\s*(?:from|import)\s+(?:{alts})\b", re.MULTILINE)
    if lang in ("javascript", "typescript"):
        return re.compile(rf"""(?:from|require\()\s*['"](?:{alts})(?:['"/])""")
    return re.compile(rf"^\s*import\s+(?:static\s+)?(?:{alts})\b", re.MULTILINE)  # java


def _plan_fetch(repo: RepoData, skills: Sequence[SkillDef], paths: list[str]) -> list[str]:
    """Every file the detectors will read, chosen up front so one fetch call serves them all."""
    wanted: list[str] = []
    live = [p for p in paths if not is_generated(p)]
    have = {name.lower() for name in repo.manifests}

    candidates = [p for p in live if _is_manifest_file(p) and not (p == _basename(p) and p.lower() in have)]
    candidates.sort(key=lambda p: (len(_parts(p)), p))
    wanted += candidates[:NESTED_MANIFEST_MAX]

    for skill in skills:
        content = skill.detectors.content
        if content is not None:
            matches = sorted(
                (p for p in live if fnmatch.fnmatch(_basename(p), content.glob)),
                key=lambda p: (len(_parts(p)), p),
            )
            wanted += matches[:CONTENT_MAX_FILES]

    sizes = {e.path: e.size for e in repo.tree}
    langs = {s.detectors.imports.lang for s in skills if s.detectors.imports is not None}
    for lang in langs:
        exts = LANG_EXTENSIONS.get(lang, ())
        files = [p for p in live if _ext(p) in exts and not _is_test_path(p)]
        files.sort(key=lambda p: (-sizes.get(p, 0), p))  # bigger files import more
        wanted += files[:IMPORT_MAX_FILES]
    return list(dict.fromkeys(wanted))


# ---------------------------------------------------------------- skill detection


def detect_skills(repo: RepoData, fetch: FileFetcher) -> tuple[dict[str, list[DetectorHit]], _Deps]:
    paths = _repo_paths(repo)
    live = [p for p in paths if not is_generated(p)]
    skills = [s for s in catalogue.load_skills() if not s.detectors.is_empty]

    wanted = _plan_fetch(repo, skills, paths)
    texts = fetch(wanted) if wanted else {}

    deps = _Deps()
    for name, text in repo.manifests.items():
        _add_manifest(deps, name, text)
    for path, text in texts.items():
        if _is_manifest_file(path):
            _add_manifest(deps, path, text)

    by_base: dict[str, str] = {}
    for p in live:
        by_base.setdefault(_basename(p), p)
    ext_count: dict[str, int] = {}
    for p in live:
        ext_count[_ext(p)] = ext_count.get(_ext(p), 0) + 1

    found: dict[str, list[DetectorHit]] = {}
    for skill in skills:
        det = skill.detectors
        hits: list[DetectorHit] = []
        hits += [DetectorHit(kind="npm", detail=n) for n in det.npm if n.lower() in deps.npm]
        hits += [DetectorHit(kind="pip", detail=n) for n in det.pip if _norm_pkg(n) in deps.pip]
        hits += [DetectorHit(kind="maven", detail=n) for n in det.maven if n.lower() in deps.maven]
        hits += [DetectorHit(kind="gradle", detail=n) for n in det.gradle if n.lower() in deps.gradle_text]
        hits += [DetectorHit(kind="file", detail=by_base[n]) for n in det.files if n in by_base]
        for prefix in det.paths:
            if any(p.startswith(prefix) or f"/{prefix}" in p for p in live) or (
                prefix == ".github/workflows/" and repo.workflow_files
            ):
                hits.append(DetectorHit(kind="path", detail=prefix))
        for ext in det.extensions:
            if ext_count.get(ext.lower(), 0) >= EXTENSION_MIN_FILES:
                hits.append(DetectorHit(kind="extension", detail=f"{ext} x{ext_count[ext.lower()]}"))
        if det.content is not None:
            regex = re.compile(det.content.regex, re.MULTILINE)
            matches = sorted(
                (p for p in live if fnmatch.fnmatch(_basename(p), det.content.glob)),
                key=lambda p: (len(_parts(p)), p),
            )
            for path in matches[:CONTENT_MAX_FILES]:
                if regex.search(texts.get(path, "")):
                    hits.append(DetectorHit(kind="content", detail=path))
                    break
        if det.imports is not None and det.imports.lang in LANG_EXTENSIONS:
            regex = _import_regex(det.imports.lang, det.imports.modules)
            exts = LANG_EXTENSIONS[det.imports.lang]
            for path, text in texts.items():
                if _ext(path) in exts and regex.search("\n".join(text.splitlines()[:IMPORT_MAX_LINES])):
                    hits.append(DetectorHit(kind="import", detail=path))
                    break
        if hits:
            found[skill.id] = hits
    return found, deps


def language_skills(repo: RepoData) -> list[str]:
    """Skills implied by the repo's primary language and topics (SCORING §1: moderate evidence)."""
    names = [repo.primary_language or "", *repo.topics]
    ids = (catalogue.normalize_skill(n) for n in names if n)
    return list(dict.fromkeys(i for i in ids if i))


# ---------------------------------------------------------------- signals

_STUDENT_HEADINGS = (
    "features?|usage|installation|screenshots?|demo|tech(?:nology)? stack|built with"
    "|architecture|api|about|overview|problem"
)
_STUDENT_SECTION = re.compile(rf"^#{{1,6}}\s*(?:{_STUDENT_HEADINGS})\b", re.IGNORECASE | re.MULTILINE)
_SETUP_WORDS = "setup|set up|install|getting started|usage|how to run|quick ?start"
_SETUP_OR_SCREENSHOT = re.compile(
    rf"^#{{1,6}}\s*.*(?:{_SETUP_WORDS})|!\[[^\]]*\]\(|<img\s|screenshot", re.IGNORECASE | re.MULTILINE
)


def is_template_readme(readme: str, templates: Sequence[str] | None = None) -> bool:
    """True if the README is still a framework starter's text.

    Heuristic for SCORING §5 `default_readme` ("matches a starter and < 300 extra chars"): a starter
    marker in the first 500 chars, a moderate length, and none of the sections a student writes
    (features, usage, screenshots, architecture ...). `data/readme_templates.txt` holds only marker
    lines, not full starter bodies, so "extra chars" cannot be measured exactly.
    """
    templates = catalogue.load_readme_templates() if templates is None else templates
    head = readme[:500].lower()
    if not any(t.lower() in head for t in templates):
        return False
    if len(readme) > TEMPLATE_README_MAX_CHARS:
        return False
    return _STUDENT_SECTION.search(readme) is None


def compute_signals(repo: RepoData) -> RepoSignals:
    paths = _repo_paths(repo)
    live = [p for p in paths if not is_generated(p)]
    bases = {_basename(p).lower() for p in paths}
    readme = repo.readme.strip()
    template = is_template_readme(readme) if readme else False

    sizes = {e.path: e.size for e in repo.tree}
    source = [p for p in live if _ext(p) in SOURCE_EXTENSIONS]
    modules: set[str] = set()
    for path in source:
        parts = _parts(path)[:-1]
        if parts and parts[0].lower() in MODULE_ROOTS:
            parts = parts[1:]
        if parts and parts[0].lower() not in NON_MODULE_DIRS and not _is_test_path(path):
            modules.add(parts[0])

    ci = (
        bool(repo.workflow_files)
        or any(p.startswith((".github/workflows/", ".circleci/")) for p in paths)
        or bool(bases & CI_FILES)
    )
    deploy = (
        bool(bases & DEPLOY_FILES)
        or any(b.startswith("dockerfile.") for b in bases)
        or any(p.startswith("k8s/") for p in paths)
    )
    total, authored = repo.total_commits, repo.authored_commits
    return RepoSignals(
        readme_chars=len(readme),
        readme_is_template=template,
        readme_substantive=len(readme) > README_SUBSTANTIVE_CHARS and not template,
        readme_has_setup_or_screenshots=bool(_SETUP_OR_SCREENSHOT.search(readme)),
        has_description=bool((repo.description or "").strip()),
        has_license=bool(repo.license) or any(b.split(".")[0] in ("license", "licence") for b in bases),
        has_demo_url=bool(repo.homepage),
        has_tests=any(_is_test_path(p) and not is_generated(p) for p in paths)
        or bool(bases & TEST_CONFIG_FILES),
        has_ci=ci,
        has_manifest=any(_is_manifest_file(p) for p in live),
        has_lockfile=bool(bases & LOCKFILES),
        module_count=len(modules),
        has_deploy_config=deploy,
        commit_facts_known=repo.has_commit_facts,
        authored_commits=authored,
        total_commits=total,
        authored_share=round(authored / total, 4) if total else 0.0,
        is_fork=repo.is_fork,
        fork_authored_commits=repo.authored_since_created if repo.is_fork else 0,
        active_span_weeks=repo.active_span_weeks,
        code_kb=round(sum(sizes.get(p, 0) for p in source) / 1024, 2),
        first_commit_share=repo.first_commit_share,
    )


def to_project_signals(signals: RepoSignals) -> ProjectSignals:
    """The subset the contract exposes on `ProjectAudit.signals` (keys match what-if `add_signals`)."""
    return ProjectSignals(
        tests=signals.has_tests,
        ci=signals.has_ci,
        demo_url=signals.has_demo_url,
        license=signals.has_license,
        readme=signals.readme_substantive,
        deploy_config=signals.has_deploy_config,
        authored_commits=signals.authored_commits,
        total_commits=signals.total_commits,
    )


def depth_parts(signals: RepoSignals) -> tuple[float, float, float]:
    """SCORING §2B Depth items: authored commits 0->30 (8), active span 0->4 weeks (6), code 0->20 KB (6)."""
    commits = min(signals.authored_commits, 30) / 30 * 8
    span = min(signals.active_span_weeks, 4) / 4 * 6
    code = min(signals.code_kb, 20) / 20 * 6
    return commits, span, code


def depth_points(signals: RepoSignals) -> float:
    """SCORING §2B Depth (0-20). Here because the `tutorial_pattern` flag needs it; scoring reuses it."""
    return round(sum(depth_parts(signals)), 2)


# ---------------------------------------------------------------- flags

_CLAIM = re.compile(r"\b(?:autonomous|agentic|ai[- ]system|ai[- ]agents?)\b", re.IGNORECASE)


def _norm_words(text: str) -> str:
    return " ".join(re.sub(r"[-_\s]+", " ", text.lower()).split())


def matches_tutorial_name(repo: RepoData, names: Sequence[str] | None = None) -> bool:
    names = catalogue.load_tutorial_names() if names is None else names
    haystacks = [_norm_words(repo.name), _norm_words(repo.description or "")]
    return any(re.search(rf"\b{re.escape(_norm_words(t))}\b", h) for t in names for h in haystacks if h)


def compute_flags(
    repo: RepoData, signals: RepoSignals, skills: dict[str, list[DetectorHit]]
) -> list[RuleFlag]:
    flags: list[RuleFlag] = []

    def add(code: FlagCode, reason: str, fix: str) -> None:
        flags.append(RuleFlag(code=code, severity=FLAG_SEVERITY[code], reason=reason, fix=fix))

    if signals.commit_facts_known:
        share = signals.first_commit_share
        untouched_fork = repo.is_fork and signals.fork_authored_commits == 0
        if untouched_fork:
            pass  # the fork flag below already says it; a second flag for one fact would double the penalty
        elif signals.authored_commits <= 3:
            add(
                "single_dump",
                f"Only {signals.authored_commits} commit(s) of yours are in this project, so the history "
                "doesn't show how it was built step by step.",
                "Commit in meaningful steps; add a CHANGELOG of what you built and when.",
            )
        elif share is not None and share >= 0.8:
            add(
                "single_dump",
                "Most of the code arrived in the first commit, so the history doesn't show how it was built.",
                "Commit in meaningful steps; add a CHANGELOG of what you built and when.",
            )
        if untouched_fork:
            add(
                "unmodified_fork",
                "This is a fork with no commits of yours after forking, so it doesn't show work of your own.",
                "Remove it from the resume or add your own feature and link the diff.",
            )
    if signals.readme_is_template:
        add(
            "default_readme",
            "The README is still the starter text, so a reader can't see what this project does.",
            "Write a README: problem, architecture diagram, setup, screenshots, results.",
        )
    if matches_tutorial_name(repo) and depth_points(signals) < 8:
        add(
            "tutorial_pattern",
            "The project name looks like a common tutorial project and its history is short, "
            "so it isn't clear what is original.",
            "Extend beyond the tutorial: add auth, tests, a deployed demo, one original feature.",
        )
    llm_dep = any(h.kind in ("npm", "pip") for h in skills.get("llm-apis", []))
    claim = _CLAIM.search(f"{repo.description or ''}\n{repo.readme[:1500]}")
    if llm_dep and claim and signals.code_kb < THIN_WRAPPER_MAX_KB:
        add(
            "thin_wrapper",
            "It calls an LLM API from a small codebase, while the description presents it as an "
            "autonomous or agentic system.",
            "Describe it accurately, or add evaluation, retrieval, tool use, and measured results.",
        )
    return flags


# ---------------------------------------------------------------- entry points


def detect(repo: RepoData, fetch: FileFetcher) -> RepoAnalysis:
    """Skills, signals and rule flags for one repo."""
    skills, _ = detect_skills(repo, fetch)
    signals = compute_signals(repo)
    return RepoAnalysis(
        repo_name=repo.name,
        skills=skills,
        language_skills=language_skills(repo),
        signals=signals,
        flags=compute_flags(repo, signals, skills),
    )


def analyse(snapshot: GithubSnapshot) -> dict[str, RepoAnalysis]:
    """Analyse every repo that has a tree or commit facts (top 8 non-forks, plus forks for the fork flag)."""
    return {
        repo.name: detect(repo, snapshot.fetcher(repo.name))
        for repo in snapshot.repos
        if repo.detailed or repo.has_commit_facts
    }
