"""A real HTTP server for the end-to-end smoke test, with every outside service faked.

    DATABASE_URL=sqlite:///./smoke.db DEV_AUTH=1 uv run python -m tests.e2e_server --port 8099

The app, routers, middleware, auth, database and background tasks are the real ones. Only what would leave the
machine is replaced: the LLM (scripted replies, written from the prompt that arrives so they always cite real
files), GitHub (the recorded UtkarshTheWise profile, plus synthetic file contents for files nobody recorded)
and portfolio pages. Used by `scripts/smoke_e2e.py`; never imported by the app.
"""

import argparse
import re
from datetime import date

import uvicorn

from app.config import Settings
from app.db.base import SessionLocal, create_all
from app.main import app
from app.routers.analyses import get_pipeline_deps
from app.services.github import GitHubClient
from app.services.pipeline import PipelineDeps
from scripts.github_fixtures import FIXTURE_ROOT, ReplayTransport
from scripts.seed_demo import seed
from tests.llm_fakes import SchemaProvider, design_judgement
from tests.test_pipeline import PAGE, RESUME, judge_reply, plan_reply

TODAY = date(2026, 10, 7)
JOB_EXTRACT = {
    "title": "Backend Engineer Intern",
    "company": "Northwind Labs",
    "location": "Chennai",
    "required_skills": ["Python", "FastAPI", "SQL", "Docker", "Kubernetes"],
    "nice_to_have": ["Redis"],
    "deadline": "2026-11-30",
}


class E2EGitHub:
    """Recorded responses where they exist; synthetic file contents for any other file request."""

    def __init__(self, db, refresh: bool):
        settings = Settings(_env_file=None, github_token="not-a-real-token")
        self._real = GitHubClient(
            db, settings, transport=ReplayTransport(FIXTURE_ROOT / "UtkarshTheWise"), refresh=refresh
        )

    @property
    def calls(self) -> int:
        return self._real.calls

    def rest_get(self, path, *, missing_ok=False):
        return self._real.rest_get(path, missing_ok=missing_ok)

    def graphql(self, query, variables):
        try:
            return self._real.graphql(query, variables)
        except AssertionError:  # not recorded: a file-contents request made by the quiz
            node = {}
            for key, value in variables.items():
                if key.startswith("e") and key[1:].isdigit():
                    path = str(value).removeprefix("HEAD:")
                    node["f" + key[1:]] = {
                        "text": "\n".join(f"# {path} line {n}" for n in range(1, 41)),
                        "isBinary": False,
                    }
            return {"repository": node}

    def close(self):
        self._real.close()


# ---------------------------------------------------------------- scripted replies, written from the prompt


def _files(user: str) -> list[tuple[str, int]]:
    """(path, number of lines) for each FILE block of a quiz prompt."""
    out = []
    for block in re.split(r"\n\n(?=FILE )", user):
        head = re.match(r"FILE (\S+)\n", block)
        if head:
            out.append((head.group(1), len(re.findall(r"^\s*\d+\| ", block, re.M))))
    return out


def quiz_reply(user: str) -> dict:
    files = _files(user)
    if not files:
        return {"questions": []}
    mode = re.search(r"^MODE: (\w+)", user, re.M).group(1)
    round_no = re.search(r"^ATTEMPT: (\d+)", user, re.M).group(1)

    def ref(i: int) -> dict:
        path, lines = files[i % len(files)]
        return {"path": path, "start_line": 1, "end_line": max(1, min(lines, 8))}

    def mcq(n: int) -> dict:
        return {
            "type": "mcq", "category": "code_reading", "source_ref": ref(n), "skill_ids": ["python"],
            "prompt": f"Attempt {round_no}, question {n}: what does the code in the cited lines do when its input is empty?",
            "options": [{"id": i, "text": f"Option {i} for question {n}"} for i in "abcd"],
            "correct_choice_id": "b", "model_answer": "It returns early because there is nothing to process.",
            "hint": "Follow the first branch.",
        }  # fmt: skip

    def short(category: str, n: int) -> dict:
        return {
            "type": "short_answer", "category": category, "source_ref": ref(n), "skill_ids": ["python", "rest-api"],
            "prompt": f"Attempt {round_no}: explain how {category.replace('_', ' ')} works for the cited lines, number {n}.",
            "key_points": ["Names the entry point", "Explains the data flow", "Mentions failure handling"],
            "acceptable_alternatives": ["Any coherent, code-consistent explanation"],
            "model_answer": "The entry point validates the input, passes it on and handles errors at the boundary.",
            "hint": "Start from the first function.",
        }  # fmt: skip

    questions = [mcq(1), mcq(2), mcq(3)]
    for n, category in enumerate(
        ["architecture", "design_decision", "debugging", "extension", "claim_check"] * 2, start=10
    ):
        questions.append(short(category, n))
    return {"questions": questions} if mode in ("verify", "practice") else {"questions": []}


def grading_by_answer(user: str) -> dict:
    """Covered when the answer says "because" (a reasoned answer), missing otherwise."""
    answers = []
    for block in user.split("\n\n---\n\n"):
        qid = re.search(r"QUESTION_ID: (\S+)", block)
        if qid is None:
            continue
        points = re.findall(
            r"^\d+\. (.+)$", block.split("Key points, in order:")[1].split("Student")[0], re.M
        )
        points = [p for p in points if not p.startswith("Acceptable")]
        reasoned = "because" in block.split("Student's answer:")[-1].lower()
        answers.append(
            {
                "question_id": qid.group(1),
                "key_points": [{"text": p, "status": "covered" if reasoned else "missing"} for p in points],
                "incorrect_statements": [],
                "feedback": "Review the entry point and how errors are handled.",
            }
        )
    return {"answers": answers}


def tailor_reply(user: str) -> dict:
    bullets = re.findall(r"^b(\d+): (.+)$", user, re.M)
    return {"bullets": [{"bullet_id": f"b{n}", "rewritten": text, "evidence_ids": []} for n, text in bullets]}


def build_deps() -> PipelineDeps:
    provider = SchemaProvider(
        {
            "ResumeProfile": RESUME,
            "ProjectJudgement": judge_reply,
            "DesignJudgement": design_judgement(),
            "RoadmapPlan": plan_reply,
            "GeneratedQuiz": quiz_reply,
            "QuizGrading": grading_by_answer,
            "JobPostingExtract": JOB_EXTRACT,
            "TailoredDraft": tailor_reply,
        }
    )
    return PipelineDeps(
        providers=[provider], github_client=E2EGitHub, fetch_page=lambda url, db, refresh: PAGE, today=TODAY
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args(argv)
    create_all()
    with SessionLocal() as db:
        seed(db, TODAY)  # the demo cohort and the demo profile's analysis
    deps = build_deps()
    app.dependency_overrides[get_pipeline_deps] = lambda: deps
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
