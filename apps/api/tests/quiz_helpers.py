"""Fakes and builders for the quiz tests: a GitHub client over a dict of files, scripted LLM replies."""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.db import models
from app.db.base import SessionLocal
from app.main import app
from app.routers.analyses import get_pipeline_deps
from app.routers.quizzes import get_clock
from app.services.pipeline import PipelineDeps, save_report
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


def make_analysis(
    db, inputs: ScoringInputs | None = None, status: str = "done", *, with_report: bool = False
) -> models.Analysis:
    """A finished analysis row. With `with_report` it also has the full stored report (as the pipeline saves
    it) and is the profile's latest, which verify results re-score."""
    inputs = inputs or inputs_with_repo()
    profile = models.Profile(name="Quiz Student", target_role_id="sde-backend")
    db.add(profile)
    db.flush()
    analysis = models.Analysis(
        profile_id=profile.id, role_id=inputs.target_role_id, status=status, progress=100,
        signals=inputs.model_dump(mode="json"),
    )  # fmt: skip
    db.add(analysis)
    db.flush()
    if with_report:
        from scripts.seed_demo import build_report

        analysis.profile = profile
        save_report(analysis, inputs, build_report(inputs, db))
    db.commit()
    return analysis


def deps(provider: SchemaProvider, github: FakeGitHub | None = None) -> PipelineDeps:
    github = github or FakeGitHub()
    return PipelineDeps(providers=[provider], github_client=lambda db, fresh: github)


class Clock:
    """A settable time source for the quiz routes."""

    def __init__(self, now: datetime = T0):
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + timedelta(seconds=seconds)


def grading_reply(status: str = "covered", incorrect: list[str] | None = None, skip: set[str] | None = None):
    """A scripted QuizGrading reply: reads the QUESTION_IDs and key points out of the prompt it is given."""

    def respond(user: str) -> dict:
        answers = []
        for block in user.split("\n\n---\n\n"):
            match = re.search(r"QUESTION_ID: (\S+)", block)
            if match is None or match.group(1) in (skip or set()):
                continue
            points = re.findall(
                r"^\d+\. (.+)$", block.split("Key points, in order:")[1].split("Student")[0], re.M
            )
            points = [p for p in points if not p.startswith("Acceptable")]
            answers.append(
                {
                    "question_id": match.group(1),
                    "key_points": [{"text": p, "status": status} for p in points],
                    "incorrect_statements": incorrect or [],
                    "feedback": "Nice work; review the connection handling once more.",
                }
            )
        return {"answers": answers}

    return respond


PROJECT = "proj-campus-api"


@dataclass
class Env:
    client: object
    provider: SchemaProvider
    clock: Clock
    analysis_id: str
    profile_id: str

    def create(self, mode: str = "verify", **kw):
        return self.client.post(
            f"/v1/analyses/{self.analysis_id}/quizzes", json={"project_id": PROJECT, "mode": mode, **kw}
        )

    def get(self, quiz_id: str):
        return self.client.get(f"/v1/quizzes/{quiz_id}")

    def answer(self, quiz_id: str, question_id: str, **kw):
        body = {"question_id": question_id, "time_taken_ms": 4000, **kw}
        return self.client.post(f"/v1/quizzes/{quiz_id}/answers", json=body)

    def submit(self, quiz_id: str):
        return self.client.post(f"/v1/quizzes/{quiz_id}/submit")

    def result(self, quiz_id: str):
        return self.client.get(f"/v1/quizzes/{quiz_id}/result")

    def questions(self, quiz_id: str) -> list[dict]:
        """The stored questions, answer keys included: for the test to know what a right answer is."""
        with SessionLocal() as db:
            rows = db.get(models.Quiz, quiz_id).questions
            return [
                {"id": q.id, "type": q.type, "correct": q.correct_choice_id, "limit": q.time_limit_s,
                 "key_points": q.key_points, "model_answer": q.model_answer}
                for q in rows
            ]  # fmt: skip

    def answer_all(
        self, quiz_id: str, text: str = "Each request opens a connection and closes it afterwards."
    ) -> None:
        for q in self.questions(quiz_id):
            self.get(quiz_id)  # serves the current question (verify)
            kw = {"choice_id": q["correct"]} if q["type"] == "mcq" else {"text": text}
            assert self.answer(quiz_id, q["id"], **kw).status_code == 200


def leaks(payload) -> list[str]:
    """Answer-key strings found anywhere in a response body."""
    text = json.dumps(payload)
    return [
        s
        for s in (
            "Opens one connection per request",
            "Closes it in a finally block",
            "It returns an empty list because",
        )
        if s in text
    ]


def new_env(
    client, provider: SchemaProvider, *, inputs: ScoringInputs | None = None, with_report: bool = False
):
    clock = Clock()
    app.dependency_overrides[get_pipeline_deps] = lambda: deps(provider, FakeGitHub())
    app.dependency_overrides[get_clock] = lambda: clock
    with SessionLocal() as db:
        analysis = make_analysis(db, inputs, with_report=with_report)
        return Env(client, provider, clock, analysis.id, analysis.profile_id)
