"""Loaders for the curated catalogues in data/ (skills, roles, resources, name lists).

Everything is read once and cached. `validate_catalogue()` runs at startup so the server
refuses to start on a broken catalogue instead of producing wrong scores.
"""

import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import DATA_DIR
from app.schemas.api import Resource, Role

MIN_RESOURCES_PER_SKILL = 2
ROLE_SKILL_RANGE = (8, 14)

SkillCategory = Literal["language", "backend", "frontend", "data", "ml", "devops", "design"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContentDetector(_Strict):
    glob: str
    regex: str


class ImportDetector(_Strict):
    lang: str
    modules: list[str]


class Detectors(_Strict):
    """Detector types from docs/SCORING.md §4. All optional; empty = no repository footprint."""

    npm: list[str] = Field(default_factory=list)
    pip: list[str] = Field(default_factory=list)
    maven: list[str] = Field(default_factory=list)
    gradle: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    paths: list[str] = Field(default_factory=list)
    extensions: list[str] = Field(default_factory=list)
    content: ContentDetector | None = None
    imports: ImportDetector | None = None

    @property
    def is_empty(self) -> bool:
        return not self.model_dump(exclude_none=True, exclude_defaults=True)


class SkillDef(_Strict):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    category: SkillCategory
    detectors: Detectors = Field(default_factory=Detectors)

    @property
    def all_aliases(self) -> list[str]:
        return [self.id, self.name, *self.aliases]


class RoleWeights(_Strict):
    skill_evidence: float
    project_quality: float
    consistency: float
    experience: float
    resume_quality: float


class RoleDef(Role):
    """The contract's Role plus the scoring weights, which the API does not expose."""

    weights: RoleWeights

    @property
    def is_design(self) -> bool:
        return self.category == "design"


class CatalogueError(ValueError):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("Invalid catalogue:\n- " + "\n- ".join(problems))


@dataclass(frozen=True)
class Catalogue:
    skills: tuple[SkillDef, ...]
    roles: tuple[RoleDef, ...]
    resources: tuple[Resource, ...]
    tutorial_names: tuple[str, ...]
    readme_templates: tuple[str, ...]


def normalize_alias(text: str) -> str:
    """'React.js' -> 'reactjs', 'C++' -> 'c++', 'CI / CD' -> 'ci/cd'. Keeps + # / as they carry meaning."""
    return re.sub(r"[^a-z0-9+#/]", "", text.lower())


def _read_lines(path: Path, comment: str) -> tuple[str, ...]:
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return tuple(line for line in lines if line and not line.startswith(comment))


def _parse(model: type[BaseModel], items: list[dict], what: str, problems: list[str]) -> list:
    parsed = []
    for item in items or []:
        try:
            parsed.append(model.model_validate(item))
        except ValidationError as exc:
            ident = item.get("id", "?") if isinstance(item, dict) else "?"
            for err in exc.errors():
                problems.append(f"{what} '{ident}': {'.'.join(map(str, err['loc']))}: {err['msg']}")
    return parsed


def read_catalogue(data_dir: Path = DATA_DIR) -> Catalogue:
    """Parse and cross-check every catalogue file. Raises CatalogueError listing all problems."""
    problems: list[str] = []
    raw_skills = yaml.safe_load((data_dir / "skills.yaml").read_text(encoding="utf-8"))["skills"]
    raw_roles = yaml.safe_load((data_dir / "roles.yaml").read_text(encoding="utf-8"))["roles"]
    raw_resources = yaml.safe_load((data_dir / "resources.yaml").read_text(encoding="utf-8"))["resources"]

    skills: list[SkillDef] = _parse(SkillDef, raw_skills, "skill", problems)
    by_id = {s.id: s for s in skills}

    # roles.yaml lists `{skill, importance}`; skill_name comes from skills.yaml.
    role_dicts = []
    for raw in raw_roles or []:
        entries = []
        for entry in raw.get("skills", []):
            skill = by_id.get(entry.get("skill"))
            if skill is None:
                problems.append(f"role '{raw.get('id')}': unknown skill '{entry.get('skill')}'")
                continue
            importance = entry.get("importance")
            if importance not in (1, 2, 3):
                problems.append(f"role '{raw.get('id')}': importance of '{skill.id}' must be 1-3")
                continue
            entries.append({"skill_id": skill.id, "skill_name": skill.name, "importance": importance})
        role_dicts.append({**raw, "skills": entries})
    roles: list[RoleDef] = _parse(RoleDef, role_dicts, "role", problems)
    resources: list[Resource] = _parse(Resource, raw_resources, "resource", problems)

    for what, ids in (("skill", raw_skills), ("role", raw_roles), ("resource", raw_resources)):
        counts = Counter(i.get("id") for i in ids or [])
        problems += [f"duplicate {what} id '{i}'" for i, n in counts.items() if n > 1]

    owners: dict[str, str] = {}
    for skill in skills:
        for alias in {normalize_alias(a) for a in skill.all_aliases}:
            if alias in owners and owners[alias] != skill.id:
                problems.append(f"alias '{alias}' belongs to both '{owners[alias]}' and '{skill.id}'")
            owners.setdefault(alias, skill.id)
        content = skill.detectors.content
        if content is not None:
            try:
                re.compile(content.regex)
            except re.error as exc:
                problems.append(f"skill '{skill.id}': content regex does not compile: {exc}")

    low, high = ROLE_SKILL_RANGE
    for role in roles:
        if not low <= len(role.skills) <= high:
            problems.append(f"role '{role.id}': has {len(role.skills)} skills, expected {low}-{high}")
        if len({s.skill_id for s in role.skills}) != len(role.skills):
            problems.append(f"role '{role.id}': lists a skill twice")
        total = sum(role.weights.model_dump().values())
        if abs(total - 1.0) > 1e-9:
            problems.append(f"role '{role.id}': weights sum to {total:.2f}, expected 1.00")

    per_skill = Counter(r.skill_id for r in resources)
    for res in resources:
        if res.skill_id not in by_id:
            problems.append(f"resource '{res.id}': unknown skill '{res.skill_id}'")
        if not res.url.startswith("https://"):
            problems.append(f"resource '{res.id}': url must start with https://")
    for skill in skills:
        if per_skill[skill.id] < MIN_RESOURCES_PER_SKILL:
            problems.append(
                f"skill '{skill.id}': has {per_skill[skill.id]} resource(s), needs {MIN_RESOURCES_PER_SKILL}"
            )

    if problems:
        raise CatalogueError(problems)
    return Catalogue(
        skills=tuple(skills),
        roles=tuple(roles),
        resources=tuple(resources),
        tutorial_names=_read_lines(data_dir / "tutorial_names.txt", "#"),
        readme_templates=_read_lines(data_dir / "readme_templates.txt", "//"),
    )


@lru_cache
def get_catalogue() -> Catalogue:
    return read_catalogue()


def validate_catalogue() -> Catalogue:
    """Load (or reuse) the catalogue; raises CatalogueError if anything is wrong."""
    return get_catalogue()


def load_skills() -> tuple[SkillDef, ...]:
    return get_catalogue().skills


def load_roles() -> tuple[RoleDef, ...]:
    return get_catalogue().roles


def load_resources() -> tuple[Resource, ...]:
    return get_catalogue().resources


def load_tutorial_names() -> tuple[str, ...]:
    return get_catalogue().tutorial_names


def load_readme_templates() -> tuple[str, ...]:
    return get_catalogue().readme_templates


def get_role(role_id: str) -> RoleDef | None:
    return next((r for r in load_roles() if r.id == role_id), None)


def get_skill(skill_id: str) -> SkillDef | None:
    return _skill_index().get(skill_id)


@lru_cache
def _skill_index() -> dict[str, SkillDef]:
    return {s.id: s for s in load_skills()}


@lru_cache
def _alias_index() -> dict[str, str]:
    return {normalize_alias(a): s.id for s in load_skills() for a in s.all_aliases}


def normalize_skill(text: str) -> str | None:
    """Map a skill as written on a resume or job post to a catalogue id; None if unknown."""
    return _alias_index().get(normalize_alias(text))


def resources_for(skill_id: str) -> list[Resource]:
    return [r for r in load_resources() if r.skill_id == skill_id]


# Aliases that are ordinary English words (or too short) and would match everywhere in free text:
# "Next steps", "node of a graph", "in the spring", "express interest", "caching headers" ...
# They still work for exact lookups through normalize_skill(); only text scanning skips them.
_TEXT_STOPLIST = {
    "go", "next", "node", "spring", "express", "caching", "layout", "charts", "dashboards", "surveys",
    "personas", "notebooks", "logging", "shell", "state management", "command line", "containers", "ia",
    "cv", "ml", "py", "ts", "js", "r", "c", "sh", "ide",
}  # fmt: skip


@lru_cache
def _text_patterns() -> tuple[tuple[str, re.Pattern[str]], ...]:
    patterns = []
    for skill in load_skills():
        words = {w.lower() for w in skill.all_aliases}
        words = {w for w in words if w not in _TEXT_STOPLIST and (len(w) >= 3 or not w.isalnum())}
        if not words:
            continue
        alts = "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in sorted(words, key=len, reverse=True))
        patterns.append((skill.id, re.compile(rf"(?<![a-z0-9+#])(?:{alts})(?![a-z0-9+#])")))
    return tuple(patterns)


def find_skills_in_text(text: str) -> set[str]:
    """Catalogue skills named in free text (an experience bullet, a project description, a certificate).

    Whole-word, case-insensitive, over skill ids, names and aliases minus an explicit stoplist of
    ambiguous words. A heuristic for *weak/moderate* evidence only; exact resume skill lists go
    through normalize_skill().
    """
    lowered = text.lower()
    return {skill_id for skill_id, pattern in _text_patterns() if pattern.search(lowered)}
