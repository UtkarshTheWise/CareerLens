"""Fakes and builders for the quiz tests: a GitHub client over a dict of files, scripted LLM replies."""

from datetime import UTC, datetime

from app.db import models
from app.services.pipeline import PipelineDeps
from app.services.scoring_inputs import ScoringInputs
from tests.llm_fakes import SchemaProvider
from tests.scoring_helpers import code_project, rich_inputs

T0 = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
REPO_URL = "https://github.com/u/campus-api"


def source(name: str, lines: int = 60) -> str:
    return "\n".join(f"# {name} line {i}" for i in range(1, lines + 1))


FILES = {
    "main.py": source("main.py"),
    "app/db.py": source("app/db.py", 80),
    "app/routes.py": source("app/routes.py", 120),
    "Dockerfile": source("Dockerfile", 12),
    "README.md": "# Campus API\n\nEvent registration for a college.\n" * 10,
}


class FakeGitHub:
    """Just enough of GitHubClient for the quiz: a tree and file blobs from a dict."""

    def __init__(self, files: dict[str, str] | None = None):
        self.files = FILES if files is None else files
        self.calls = 0

    def rest_get(self, path: str, *, missing_ok: bool = False):
        self.calls += 1
        return {"tree": [{"path": p, "type": "blob", "size": len(t)} for p, t in self.files.items()]}

    def graphql(self, query: str, variables: dict):
        self.calls += 1
        node = {}
        for key, value in variables.items():
            if key.startswith("e"):
                text = self.files.get(value.removeprefix("HEAD:"))
                node["f" + key[1:]] = {"text": text, "isBinary": False} if text is not None else None
        return {"repository": node}


def mcq(category: str = "code_reading", path: str = "main.py", start: int = 3, end: int = 12, **kw) -> dict:
    base = {
        "type": "mcq", "category": category, "prompt": "What happens when the scores list is empty here?",
        "source_ref": {"path": path, "start_line": start, "end_line": end},
        "skill_ids": ["python"],
        "options": [{"id": "a", "text": "It raises"}, {"id": "b", "text": "It returns an empty list"},
                    {"id": "c", "text": "It loops forever"}, {"id": "d", "text": "It returns None"}],
        "correct_choice_id": "b", "model_answer": "It returns an empty list because the loop never runs.",
        "hint": "Follow the loop.",
    }  # fmt: skip
    return {**base, **kw}


def short(category: str, path: str = "app/db.py", start: int = 5, end: int = 30, **kw) -> dict:
    base = {
        "type": "short_answer", "category": category,
        "prompt": f"Explain how {category.replace('_', ' ')} works in this project.",
        "source_ref": {"path": path, "start_line": start, "end_line": end},
        "skill_ids": ["python", "sql"],
        "key_points": ["Opens one connection per request", "Closes it in a finally block", "Uses SQLite"],
        "acceptable_alternatives": ["A connection pool would also work"],
        "model_answer": "Each request opens a connection and closes it afterwards.", "hint": "Look at get_db.",
    }  # fmt: skip
    return {**base, **kw}


def full_verify_reply() -> dict:
    return {
        "questions": [
            mcq(prompt="What does the first helper return for an empty list?"),
            mcq(
                path="app/routes.py",
                start=10,
                end=22,
                prompt="Which status code does the route send on a miss?",
            ),
            short("architecture", prompt="Trace a request from the route to the database."),
            short("design_decision", prompt="Why does db.py use SQLite and what breaks first at scale?"),
            short("debugging", prompt="Two requests update the same row at once. What can go wrong?"),
            short("extension", prompt="How would you add pagination to the list route?"),
        ]
    }


def inputs_with_repo() -> ScoringInputs:
    base = rich_inputs()
    project = code_project(
        "campus-api", skills=["python", "sql", "docker"], claimed_skill_ids=["python", "sql"]
    )
    return base.model_copy(update={"projects": [project]})


def make_analysis(db, inputs: ScoringInputs | None = None, status: str = "done") -> models.Analysis:
    inputs = inputs or inputs_with_repo()
    profile = models.Profile(name="Quiz Student", target_role_id="sde-backend")
    db.add(profile)
    db.flush()
    analysis = models.Analysis(
        profile_id=profile.id, role_id=inputs.target_role_id, status=status, progress=100,
        signals=inputs.model_dump(mode="json"),
    )  # fmt: skip
    db.add(analysis)
    db.commit()
    return analysis


def deps(provider: SchemaProvider, github: FakeGitHub | None = None) -> PipelineDeps:
    github = github or FakeGitHub()
    return PipelineDeps(providers=[provider], github_client=lambda db, fresh: github)
