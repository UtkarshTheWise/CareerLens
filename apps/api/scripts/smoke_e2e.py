"""End-to-end smoke test over real HTTP, in both auth modes.

    cd apps/api
    uv run python scripts/smoke_e2e.py              # dev mode (DEV_AUTH=1) then token mode (DEV_AUTH=0)
    uv run python scripts/smoke_e2e.py --mode token

For each mode it starts `tests/e2e_server.py` (the real app; LLM, GitHub and portfolio pages faked) on a
throwaway SQLite database, walks the whole product through the HTTP API and checks every response against
`contracts/openapi.yaml`. It also asserts the product rules that must never break: quiz answer keys never
appear before grading, focus-loss data never reaches the cohort endpoints, cohort data is staff-only in token
mode, and a weak result is described as "understanding not demonstrated yet", never as "didn't build it".
Exits 1 on the first failed check.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import jwt
import yaml
from jsonschema import Draft202012Validator

API_DIR = Path(__file__).resolve().parent.parent
CONTRACT = yaml.safe_load((API_DIR.parent.parent / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
RESUME = API_DIR / "tests" / "fixtures" / "resume.pdf"
SECRET = "smoke-secret-smoke-secret-smoke-secret-32"
STAFF_EMAIL = "coordinator@college.edu"
PORT = 8099
KEY_FIELDS = ("correct_choice_id", "model_answer", "feedback", "source_ref", "score")
OPERATIONS = {
    op["operationId"]: (path, method)
    for path, item in CONTRACT["paths"].items()
    for method, op in item.items()
    if method in ("get", "post", "put", "patch", "delete")
}
checks = 0


def check(condition: bool, what: str) -> None:
    global checks
    checks += 1
    if not condition:
        raise SystemExit(f"FAILED: {what}")
    print(f"  ok  {what}")


class Client:
    def __init__(self, base: str, token: str | None = None):
        self.http = httpx.Client(base_url=base, timeout=60)
        self.token = token

    def call(
        self,
        operation: str,
        expect: int | tuple[int, ...] = 200,
        *,
        path=None,
        query=None,
        body=None,
        files=None,
        data=None,
    ):
        template, method = OPERATIONS[operation]
        url = template.format(**(path or {}))
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        res = self.http.request(
            method.upper(), url, params=query, json=body, files=files, data=data, headers=headers
        )
        allowed = (expect,) if isinstance(expect, int) else expect
        check(res.status_code in allowed, f"{operation} -> {res.status_code} (wanted {allowed})")
        self.validate(operation, res)
        return res

    @staticmethod
    def validate(operation: str, res: httpx.Response) -> None:
        template, method = OPERATIONS[operation]
        responses = CONTRACT["paths"][template][method]["responses"]
        spec = responses.get(str(res.status_code)) or responses.get("default")
        if spec and "$ref" in spec:
            spec = CONTRACT["components"]["responses"][spec["$ref"].rsplit("/", 1)[-1]]
        content = (spec or {}).get("content", {})
        media = res.headers.get("content-type", "").split(";")[0]
        schema = (content.get(media) or {}).get("schema")
        if schema is None or media != "application/json":
            return
        root = {"components": CONTRACT["components"], **schema}
        errors = list(Draft202012Validator(root).iter_errors(res.json()))
        check(
            not errors,
            f"{operation} body matches the contract" + (f": {errors[0].message[:160]}" if errors else ""),
        )


def token_for(sub: str, **claims) -> str:
    payload = {"sub": sub, "aud": "authenticated", "exp": int(time.time()) + 3600, **claims}
    return jwt.encode(payload, SECRET, "HS256")


def start_server(mode: str, db_path: Path, log_path: Path) -> subprocess.Popen:
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        "DEV_AUTH": "1" if mode == "dev" else "0",
        "SUPABASE_JWT_SECRET": SECRET,
        "PLACEMENT_STAFF": STAFF_EMAIL,
        "QUIZ_COOLDOWN_MINUTES": "0",
        "LOG_LEVEL": "WARNING",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(API_DIR),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "tests.e2e_server", "--port", str(PORT)], cwd=API_DIR, env=env,
        stdout=log_path.open("w", encoding="utf-8"), stderr=subprocess.STDOUT,
    )  # fmt: skip
    for _ in range(120):
        try:
            if httpx.get(f"http://127.0.0.1:{PORT}/health", timeout=2).status_code == 200:
                return proc
        except httpx.HTTPError:
            time.sleep(0.5)
    proc.kill()
    raise SystemExit("FAILED: the e2e server did not start")


def no_keys(payload, where: str) -> None:
    """Nothing that reveals an answer may appear in a verify response before grading."""
    text = json.dumps(payload)
    for questions in [payload.get("questions", [])] if isinstance(payload, dict) else []:
        for q in questions:
            check(
                "correct_choice_id" not in q and "key_points" not in q and "model_answer" not in q,
                f"{where}: question {q['order']} carries no key",
            )
    check("Option b for question" not in text or "correct" not in text, f"{where}: no marked-correct option")


def poll_analysis(c: Client, analysis_id: str) -> dict:
    for _ in range(120):
        body = c.call("getAnalysis", path={"analysis_id": analysis_id}).json()
        if body["status"] in ("done", "failed"):
            return body
        time.sleep(1)
    raise SystemExit("FAILED: analysis did not finish")


def run_quiz_round(c: Client, analysis_id: str, project_id: str, reasoned: bool) -> dict:
    created = c.call(
        "createQuiz",
        201,
        path={"analysis_id": analysis_id},
        body={"project_id": project_id, "mode": "verify"},
    ).json()
    check(
        created["questions"] == [] and created["total_questions"] >= 4,
        "verify quiz is created with no questions shown yet",
    )
    for n in range(created["total_questions"]):
        shown = c.call("getQuiz", path={"quiz_id": created["id"]}).json()
        current = shown["questions"][-1]
        check(
            not current["answered"] and current["time_remaining_s"] is not None,
            f"question {n + 1} is served with a running clock",
        )
        no_keys(shown, f"getQuiz {n + 1}")
        body = {"question_id": current["id"], "time_taken_ms": 9000, "focus_lost_count": 2}
        if current["type"] == "mcq":
            body["choice_id"] = current["options"][0]["id"]
        else:
            body["text"] = (
                "It validates the input because the entry point is the boundary, then passes it on."
                if reasoned
                else "No idea."
            )
        fb = c.call("answerQuizQuestion", path={"quiz_id": created["id"]}, body=body).json()
        check(
            fb["recorded"]
            and fb["score"] is None
            and fb["model_answer"] is None
            and fb["correct_choice_id"] is None,
            f"answer {n + 1} is recorded without any grading detail",
        )
    result = c.call("submitQuiz", path={"quiz_id": created["id"]}).json()
    check(
        result["flag"] is not None or result["understanding"] != "not_demonstrated",
        "a not-demonstrated result raises the understanding flag",
    )
    check(result["score_update"] is not None, "submit returns the score change")
    check(
        result["focus_lost_total"] == 2 * created["total_questions"],
        "the student sees their own focus-loss count",
    )
    check(
        c.call("getQuizResult", path={"quiz_id": created["id"]}).json() == result,
        "getQuizResult returns the same body",
    )
    return result


def walk(mode: str, base: str, secure: bool) -> None:
    student = Client(base, token_for("smoke-student", email="student@college.edu") if secure else None)
    staff = Client(base, token_for("smoke-staff", email=STAFF_EMAIL) if secure else None)

    print("health and catalogue")
    health = student.call("getHealth").json()
    check(health["status"] == "ok" and health["version"], "health is ok")
    check(len(student.call("listRoles").json()) == 7, "seven roles")
    if secure:
        anon = Client(base)
        anon.call("listRoles", 401)
        Client(base, token_for("x") + "tamper").call("listRoles", 401)
        student.call("getMe", 404)

    print("profile, resume, analysis")
    profile = student.call(
        "createProfile",
        201,
        body={"name": "Smoke Student", "github_username": "UtkarshTheWise", "target_role_id": "sde-backend"},
    ).json()
    pid = profile["id"]
    student.call(
        "uploadDocument",
        200,
        path={"profile_id": pid},
        data={"kind": "resume"},
        files={"file": ("resume.pdf", RESUME.read_bytes())},
    )
    started = student.call(
        "startAnalysis", 202, path={"profile_id": pid}, body={"role_id": "sde-backend"}
    ).json()
    done = poll_analysis(student, started["id"])
    check(
        done["status"] == "done" and done["report"] is not None,
        f"analysis finishes with a report (status {done['status']}, error {done.get('error')})",
    )
    report = done["report"]
    check(
        0 <= report["score"]["total"] <= 100 and report["score"]["components"],
        "score breakdown has components with reasons",
    )
    check(all(c["reasons"] for c in report["score"]["components"]), "every component explains itself")
    check(
        len(student.call("listAnalyses", path={"profile_id": pid}).json()) == 1, "analysis history lists it"
    )
    check(
        student.call("getMe").json()["latest_analysis_id"] == started["id"],
        "getMe points at the latest analysis",
    )

    print("what-if and roadmap")
    code = next(p for p in report["projects"] if p["kind"] == "code" and p["counted_in_score"])
    sim = student.call(
        "simulateAnalysis",
        path={"analysis_id": started["id"]},
        body={"changes": [{"project_id": code["project_id"], "add_signals": ["tests", "ci"]}]},
    ).json()
    check(sim["after"]["total"] >= sim["before"]["total"], "adding tests and CI never lowers the score")
    ms = report["roadmap"][0]
    ticked = student.call(
        "updateMilestone", path={"analysis_id": started["id"], "milestone_id": ms["id"]}, body={"done": True}
    ).json()
    check(ticked["done"] is True, "a roadmap milestone can be ticked")
    check(
        student.call("getAnalysis", path={"analysis_id": started["id"]}).json()["report"]["score"]["total"]
        == report["score"]["total"],
        "ticking a milestone does not change the score",
    )

    print("practice quiz")
    practice = student.call(
        "createQuiz",
        201,
        path={"analysis_id": started["id"]},
        body={"project_id": code["project_id"], "mode": "practice", "question_count": 6},
    ).json()
    check(
        len(practice["questions"]) == 6 and all(q["hint"] for q in practice["questions"]),
        "practice quiz shows all questions with hints",
    )
    check(
        "correct_choice_id" not in json.dumps(practice) and "key_points" not in json.dumps(practice),
        "practice questions carry no answer key",
    )
    first = practice["questions"][0]
    fb = student.call(
        "answerQuizQuestion",
        path={"quiz_id": practice["id"]},
        body={"question_id": first["id"], "choice_id": "a", "time_taken_ms": 4000},
    ).json()
    check(
        fb["correct_choice_id"] and fb["model_answer"] and fb["source_ref"],
        "practice feedback reveals the answer and the lines after answering",
    )
    before_practice = student.call("getAnalysis", path={"analysis_id": started["id"]}).json()["report"][
        "score"
    ]["total"]
    pres = student.call("submitQuiz", path={"quiz_id": practice["id"]}).json()
    check(pres["understanding"] is None and pres["score_update"] is None, "practice never changes evidence")
    check(
        student.call("getAnalysis", path={"analysis_id": started["id"]}).json()["report"]["score"]["total"]
        == before_practice,
        "practice leaves the score alone",
    )

    print("verify quiz: a weak result, then a retake")
    weak = run_quiz_round(student, started["id"], code["project_id"], reasoned=False)
    check(
        weak["understanding"] == "not_demonstrated" and weak["flag"]["code"] == "understanding_gap",
        "weak answers give understanding_gap",
    )
    text = json.dumps(weak).lower()
    check(
        "didn't build" not in text
        and "did not build" not in text
        and "fake" not in text
        and "slop" not in text,
        "the copy never says the student did not build it",
    )
    after_weak = student.call("getAnalysis", path={"analysis_id": started["id"]}).json()["report"]
    check(
        after_weak["score"]["total"] == weak["score_update"]["after"]["total"],
        "the report shows the post-quiz score",
    )
    check(
        any("understanding-gap" in a for m in after_weak["roadmap"] for a in m["addresses"]),
        "a review milestone appears in the roadmap",
    )
    check(
        next(p for p in after_weak["projects"] if p["project_id"] == code["project_id"])["understanding"]
        == "not_demonstrated",
        "the project shows understanding not demonstrated yet",
    )
    strong = run_quiz_round(student, started["id"], code["project_id"], reasoned=True)
    check(
        strong["understanding"] == "demonstrated" and strong["flag"] is None,
        "reasoned answers on a retake demonstrate understanding",
    )
    check(
        strong["score_update"]["after"]["total"] > strong["score_update"]["before"]["total"],
        "the score recovers and gains after a demonstrated retake",
    )
    listing = student.call("listQuizzes", path={"profile_id": pid}).json()
    check(len(listing) == 3 and listing[0]["understanding"] == "demonstrated", "quiz history is newest first")

    print("job match, applications, tailoring")
    posting = {
        "title": "Backend Engineer Intern",
        "company": "Northwind Labs",
        "description": "Build REST APIs in Python (FastAPI) on SQL with Docker, deployed to Kubernetes.",
        "required_skills": ["Python", "FastAPI", "SQL", "Docker", "Kubernetes"],
        "nice_to_have": ["Redis"],
        "source": "jsonld",
    }
    match = student.call("matchJob", body={"profile_id": pid, "posting": posting}).json()
    check(
        match["evidence_match"] <= match["keyword_match"] <= 100, "evidence match never exceeds keyword match"
    )
    llm_match = student.call(
        "matchJob",
        body={
            "profile_id": pid,
            "posting": {**posting, "required_skills": [], "nice_to_have": [], "source": "llm"},
        },
    ).json()
    check(
        llm_match["normalized_posting"]["required_skills"], "a page with no skills is read by the extractor"
    )
    app_row = student.call(
        "createApplication",
        201,
        body={
            "profile_id": pid,
            "company": "Northwind Labs",
            "title": "Backend Engineer Intern",
            "description": posting["description"],
            "keyword_match": match["keyword_match"],
            "evidence_match": match["evidence_match"],
        },
    ).json()
    check(app_row["status"] == "saved", "applications start as saved")
    moved = student.call(
        "updateApplication", path={"application_id": app_row["id"]}, body={"status": "applied"}
    ).json()
    check(moved["status"] == "applied" and moved["applied_at"], "moving to applied stamps the time")
    tailored = student.call("tailorResume", path={"application_id": app_row["id"]}).json()
    check(
        tailored["bullets"] and all(b["original"] for b in tailored["bullets"]),
        "tailoring returns the student's own bullets",
    )
    check(
        len(student.call("listApplications", query={"profile_id": pid}).json()) == 1,
        "the tracker lists the application",
    )
    student.call("deleteApplication", 204, path={"application_id": app_row["id"]})

    print("cohorts and privacy")
    if secure:
        student.call("listCohorts", 403)
    cohorts = staff.call("listCohorts").json()
    check(cohorts and cohorts[0]["student_count"] == 40, "the seeded cohort has 40 students")
    cid = cohorts[0]["id"]
    insights = staff.call(
        "getCohortInsights", path={"cohort_id": cid}, query={"role_id": "sde-backend"}
    ).json()
    check(
        insights["analysed_count"] == 40 and sum(insights["bands"].values()) == 40,
        "insights cover all 40 students",
    )
    check(insights["understanding"]["quizzed"] > 0, "the cohort shows understanding statuses")
    students = staff.call(
        "listCohortStudents",
        path={"cohort_id": cid},
        query={"role_id": "sde-backend", "at_risk_only": "true"},
    ).json()
    check(students and all(s["at_risk"] for s in students), "the at-risk filter works")
    csv = staff.call("exportCohort", path={"cohort_id": cid}, query={"role_id": "sde-backend"})
    check(
        csv.headers["content-type"].startswith("text/csv") and csv.text.count("\n") >= 40,
        "the CSV export has a row per student",
    )
    private = json.dumps([insights, students]).lower() + csv.text.lower()
    check(
        "focus" not in private and "model_answer" not in private and "key_point" not in private,
        "no focus data or answer detail reaches the cohort endpoints",
    )

    if secure:
        print("isolation between users")
        other = Client(base, token_for("someone-else", email="other@college.edu"))
        other.call("getProfile", 404, path={"profile_id": pid})
        other.call("getAnalysis", 404, path={"analysis_id": started["id"]})
        other.call("getQuiz", 404, path={"quiz_id": practice["id"]})
        check(True, "another user cannot read this student's profile, analysis or quiz")
    student.call("deleteProfile", 204, path={"profile_id": pid})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--mode", choices=["dev", "token", "both"], default="both")
    modes = ["dev", "token"] if parser.parse_args().mode == "both" else [parser.parse_args().mode]
    for mode in modes:
        print(f"\n=== {mode} mode ===")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            log_path = Path(tmp) / "server.log"
            server = start_server(mode, Path(tmp) / "smoke.db", log_path)
            try:
                walk(mode, f"http://127.0.0.1:{PORT}", secure=mode == "token")
            except SystemExit:
                print("--- server log (tail)")
                for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-12:]:
                    try:  # JSON log lines: show the message and the end of any traceback
                        entry = json.loads(line)
                        print(entry.get("level"), entry.get("logger"), entry.get("msg"))
                        print("\n".join(entry.get("exc", "").splitlines()[-8:]))
                    except ValueError:
                        print(line)
                raise
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
    print(f"\nAll {checks} checks passed.")


if __name__ == "__main__":
    main()
