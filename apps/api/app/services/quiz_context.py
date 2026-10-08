"""What a quiz is written from (docs/QUIZ.md section 2): the student's own key files or case-study page.

No LLM here. `select_files` is a pure choice over the repository tree and the stored detector hits;
`build_code_context` / `build_design_context` turn fetched text into a `QuizContext`, which also answers
"does this source_ref exist?" for the question validator. Fetching itself (GitHub, portfolio page) is
injected, so tests never touch the network.
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from app import catalogue
from app.services.detectors import SOURCE_EXTENSIONS, is_generated
from app.services.github import TreeEntry
from app.services.portfolio import PageText
from app.services.scoring_inputs import ProjectInput

MAX_FILES = 5
MAX_FILE_CHARS = 6_000
MAX_TOTAL_CHARS = 20_000
README_CHARS = 2_000
PAGE_CHARS = 6_000
MIN_USEFUL_CHARS = 500  # don't squeeze a file into what is left of the budget below this

_ENTRY_STEMS = {"main", "app", "manage", "server", "index"}
_TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs", "e2e"}
_REPO_URL = re.compile(r"github\.com/([^/\s]+)/([^/\s#?]+)")


def _names(skill_ids: Sequence[str]) -> dict[str, str]:
    return {s: skill.name for s in dict.fromkeys(skill_ids) if (skill := catalogue.get_skill(s)) is not None}


def repo_from_url(url: str | None) -> tuple[str, str] | None:
    match = _REPO_URL.search(url or "")
    if not match:
        return None
    return match.group(1), match.group(2).removesuffix(".git")


def _base(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _ext(path: str) -> str:
    base = _base(path)
    return base[base.rfind(".") :].lower() if "." in base else ""


def _is_test(path: str) -> bool:
    parts = path.lower().split("/")
    base = parts[-1]
    return (
        any(p in _TEST_DIRS for p in parts[:-1])
        or base.startswith("test_")
        or base.endswith(("_test.py", "_test.go"))
        or ".test." in base
        or ".spec." in base
    )


def _is_source(path: str) -> bool:
    return _ext(path) in SOURCE_EXTENSIONS and not is_generated(path)


def _is_entry(path: str) -> bool:
    parts = path.split("/")
    if len(parts) > 3 or not _is_source(path) or _is_test(path):
        return False
    stem = _base(path).rsplit(".", 1)[0].lower()
    return stem in _ENTRY_STEMS or (stem == "page" and parts[:-1] == ["app"])


def select_files(tree: Sequence[TreeEntry], project: ProjectInput) -> list[str]:
    """Up to five paths: entry points, files that triggered detectors (claimed skills first), then the
    largest source files. Generated, vendored, minified and test files are never chosen."""
    size = {e.path: e.size for e in tree}
    entries = sorted((p for p in size if _is_entry(p)), key=lambda p: (p.count("/"), -size[p], p))[:2]

    claimed = [s for s in project.claimed_skill_ids if s in project.skills]
    others = sorted(s for s in project.skills if s not in claimed)
    hits: list[str] = []
    for skill in [*claimed, *others]:
        for hit in project.skills[skill]:
            path = hit.detail
            if hit.kind in ("file", "content", "import") and path in size and not is_generated(path):
                if path not in hits and not _is_test(path):
                    hits.append(path)

    largest = sorted(
        (p for p in size if _is_source(p) and not _is_test(p) and size[p] > 0), key=lambda p: (-size[p], p)
    )
    chosen: list[str] = []
    for group in (entries, hits[:2], largest, hits, entries):  # later groups only top up
        for path in group:
            if path not in chosen and len(chosen) < MAX_FILES:
                chosen.append(path)
    return chosen


def _cut(text: str, limit: int) -> list[str]:
    """The first `limit` characters, ending on a whole line."""
    lines = text.replace("\r\n", "\n").split("\n")
    out, used = [], 0
    for line in lines:
        if used + len(line) + 1 > limit:
            break
        out.append(line)
        used += len(line) + 1
    return out


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


@dataclass
class QuizContext:
    kind: Literal["code", "design"]
    title: str
    url: str | None  # repository URL, or the case-study page URL
    description: str = ""
    readme: str = ""
    files: dict[str, list[str]] = field(default_factory=dict)  # path -> lines, as shown to the model
    page_text: str = ""
    claimed: dict[str, str] = field(default_factory=dict)  # skill id -> name, as the resume claims it
    detected: dict[str, str] = field(default_factory=dict)  # skill id -> name, found in the repository

    def has_range(self, path: str, start: int | None, end: int | None) -> bool:
        lines = self.files.get(path)
        if lines is None or start is None or end is None:
            return False
        return 1 <= start <= end <= len(lines)

    def has_page(self, path: str) -> bool:
        return self.kind == "design" and path == self.url

    def has_section(self, section: str | None) -> bool:
        needle = _normalise(section or "")
        return len(needle) >= 3 and needle in _normalise(self.page_text)

    def numbered(self, path: str) -> str:
        return "\n".join(f"{n:>4}| {line}" for n, line in enumerate(self.files[path], start=1))

    def excerpt(self, path: str, start: int, end: int, limit: int = 30) -> str:
        """Lines start..end (1-based, inclusive) as plain text, at most `limit` lines."""
        return "\n".join(self.files[path][start - 1 : min(end, start - 1 + limit)])

    def blob_url(self, path: str, start: int | None, end: int | None) -> str | None:
        if self.kind == "design":
            return self.url
        if not self.url:
            return None
        anchor = f"#L{start}-L{end}" if start and end else ""
        return f"{self.url}/blob/HEAD/{path}{anchor}"

    def prompt_material(self) -> str:
        """The files (numbered) or the page text, ready to put in the prompt."""
        if self.kind == "design":
            return f"CASE STUDY PAGE ({self.url}):\n{self.page_text}"
        return "\n\n".join(f"FILE {path}\n{self.numbered(path)}" for path in self.files)


def build_code_context(
    project: ProjectInput,
    tree: Sequence[TreeEntry],
    fetch: Callable[[Sequence[str]], dict[str, str]],
    *,
    description: str = "",
) -> QuizContext:
    """Fetch the selected files (one call, with the README) and cut them to the budget."""
    chosen = select_files(tree, project)
    readme_path = next(
        (e.path for e in tree if "/" not in e.path and e.path.lower().startswith("readme")), None
    )
    wanted = [*chosen, *([readme_path] if readme_path else [])]
    fetched = fetch(wanted) if wanted else {}

    files: dict[str, list[str]] = {}
    budget = MAX_TOTAL_CHARS
    for path in chosen:
        text = fetched.get(path)
        if not text or not text.strip():
            continue
        limit = min(MAX_FILE_CHARS, budget)
        if limit < MIN_USEFUL_CHARS:
            break
        lines = _cut(text, limit)
        if not lines:
            continue
        files[path] = lines
        budget -= sum(len(line) + 1 for line in lines)
    readme = (fetched.get(readme_path or "") or "")[:README_CHARS]
    return QuizContext(
        kind="code",
        title=project.title,
        url=project.url,
        description=description,
        readme=readme,
        files=files,
        claimed=_names(project.claimed_skill_ids),
        detected=_names([*project.skills, *project.language_skills]),
    )


def build_design_context(project: ProjectInput, page: PageText, *, description: str = "") -> QuizContext:
    return QuizContext(
        kind="design",
        title=project.title,
        url=project.url,
        description=description,
        page_text=(page.text or "")[:PAGE_CHARS] if page.readable else "",
        claimed=_names(project.claimed_skill_ids),
    )
