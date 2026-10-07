"""Project Understanding Check: creating a quiz (docs/QUIZ.md sections 2 and 4).

`create_quiz` collects the project's own material (no LLM), asks the model for questions, drops every
question that cites something that is not in the material, picks the mix the mode needs and stores the
questions with their answer keys. Grading, timing and the effect on the score live in `quiz_grading.py`,
`quiz_timing.py` and `quiz_effects.py`.
"""

import logging
import random
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import catalogue
from app.db import models
from app.errors import ApiError, not_found
from app.prompts import load_prompt
from app.schemas.api import AnalysisReport, QuizCreate, QuizMode
from app.schemas.llm import GeneratedQuestion, GeneratedQuiz
from app.services.github import GitHubClient, TreeEntry, fetch_files
from app.services.llm import LLMError, generate_structured
from app.services.pipeline import PipelineDeps
from app.services.portfolio import fetch_page
from app.services.quiz_context import QuizContext, build_code_context, build_design_context, repo_from_url
from app.services.scoring import slug
from app.services.scoring_inputs import ProjectInput, ScoringInputs

logger = logging.getLogger("careerlens.quiz")

VERIFY_QUESTIONS = 6
PRACTICE_DEFAULT = 6
MIN_QUESTIONS = {"verify": 4, "practice": 3}
MCQ_SECONDS = 60
SHORT_SECONDS = 180
SNIPPET_MAX_LINES = 30
SNIPPET_MAX_RANGE = 40
LANGUAGES = {
    ".py": "python", ".js": "javascript", ".jsx": "jsx", ".ts": "typescript", ".tsx": "tsx", ".java": "java",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php", ".cs": "csharp", ".kt": "kotlin", ".c": "c",
    ".cpp": "cpp", ".html": "html", ".css": "css", ".sql": "sql", ".sh": "bash", ".vue": "vue",
}  # fmt: skip


@dataclass(frozen=True)
class Slot:
    """One wanted question: any of these categories, of this type."""

    categories: tuple[str, ...]
    type: str

    def describe(self) -> str:
        return f"{' or '.join(self.categories)} ({self.type})"


def mix_for(mode: str, kind: str, count: int = PRACTICE_DEFAULT) -> list[Slot]:
    """The question mix of docs/QUIZ.md section 2. MCQ is at most a third of the questions."""
    short = "short_answer"
    if mode == "verify" and kind == "code":
        return [
            Slot(("code_reading",), "mcq"), Slot(("code_reading",), "mcq"), Slot(("architecture",), short),
            Slot(("design_decision",), short), Slot(("debugging",), short),
            Slot(("extension", "claim_check"), short),
        ]  # fmt: skip
    if mode == "verify":
        return [
            Slot(("process",), short), Slot(("process",), short), Slot(("design_decision",), short),
            Slot(("design_decision",), short), Slot(("outcome",), short), Slot(("critique",), short),
        ]  # fmt: skip
    if kind == "design":
        cycle = [Slot((c,), short) for c in ("process", "design_decision", "outcome", "critique")]
        return [cycle[i % 4] for i in range(count)]
    mcqs = max(1, count // 3)
    cycle = [
        Slot(("architecture",), short), Slot(("design_decision",), short), Slot(("debugging",), short),
        Slot(("extension", "claim_check"), short),
    ]  # fmt: skip
    return [Slot(("code_reading",), "mcq")] * mcqs + [cycle[i % 4] for i in range(count - mcqs)]


# ---------------------------------------------------------------- validation


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


def validate_question(q: GeneratedQuestion, ctx: QuizContext) -> GeneratedQuestion | None:
    """The question if it is usable, else None. Cites only what exists in the material."""
    if len(_clean(q.prompt)) < 15 or not _clean(q.model_answer):
        return None
    ref = q.source_ref
    if q.category != "claim_check":
        if ref is None:
            return None
        if ctx.kind == "code":
            if not ctx.has_range(ref.path, ref.start_line, ref.end_line):
                return None
        elif not ctx.has_section(ref.section):
            return None
    skill_ids = [s for s in dict.fromkeys(q.skill_ids) if catalogue.get_skill(s) is not None]
    update: dict = {"skill_ids": skill_ids}
    if ctx.kind == "design":
        if q.type == "mcq":
            return None  # case studies are self-reported; no multiple choice (QUIZ.md section 6)
        if ref is not None:
            update["source_ref"] = ref.model_copy(update={"path": ctx.url or ref.path})
    if q.type == "mcq":
        ids = [o.id for o in q.options]
        texts = [_clean(o.text) for o in q.options]
        if len(ids) != 4 or len(set(ids)) != 4 or len(set(texts)) != 4 or not all(texts):
            return None
        if q.correct_choice_id not in ids:
            return None
    else:
        points = [_clean(k) for k in q.key_points if _clean(k)]
        if len(points) < 3:
            return None
        update["key_points"] = points[:5]
    return q.model_copy(update=update)


def pick(valid: list[GeneratedQuestion], slots: list[Slot]) -> tuple[list[GeneratedQuestion | None], int]:
    """Fill each slot from the valid questions: exact category first, then any of the right type."""
    chosen: list[GeneratedQuestion | None] = [None] * len(slots)
    used: set[int] = set()
    for strict in (True, False):
        for i, slot in enumerate(slots):
            if chosen[i] is not None:
                continue
            for j, q in enumerate(valid):
                if j in used or q.type != slot.type or (strict and q.category not in slot.categories):
                    continue
                chosen[i] = q
                used.add(j)
                break
    return chosen, sum(1 for c in chosen if c is None)


# ---------------------------------------------------------------- generation


def _skill_list(skills: dict[str, str]) -> str:
    return ", ".join(f"{sid}: {name}" for sid, name in skills.items()) or "(none)"


def _mix_text(slots: list[Slot]) -> str:
    counts = Counter(s.describe() for s in slots)
    return "\n".join(f"- {n} × {what}" for what, n in counts.items())


def generate_questions(
    ctx: QuizContext,
    slots: list[Slot],
    mode: str,
    attempt: int,
    db: Session,
    providers,
) -> list[GeneratedQuestion]:
    """Ask for the mix, validate, and ask once more for whatever is missing."""
    prompt = load_prompt("quiz_generate")
    minimum = min(MIN_QUESTIONS[mode], len(slots))

    def ask(slots_wanted: list[Slot], extra: str) -> list[GeneratedQuestion]:
        user = prompt.user(
            mode=mode,
            kind=ctx.kind,
            title=ctx.title,
            attempt=str(attempt),
            mix=_mix_text(slots_wanted),
            extra=extra,
            description=ctx.description or "(none given)",
            claimed=_skill_list(ctx.claimed),
            detected=_skill_list(ctx.detected),
            readme=ctx.readme or "(none)",
            material=ctx.prompt_material() or "(none)",
        )
        result = generate_structured(
            GeneratedQuiz, prompt.system, user, tier="smart", db=db, providers=providers
        )
        return [v for q in result.questions if (v := validate_question(q, ctx)) is not None]

    valid = ask(slots, "")
    chosen, missing = pick(valid, slots)
    if missing:
        wanted = [s for s, c in zip(slots, chosen, strict=True) if c is None]
        seen = "; ".join(_clean(q.prompt)[:80] for q in valid)
        extra = (
            f"\nREPLACEMENTS: you already wrote {len(valid)} usable questions ({seen}). "
            f"Write only the {len(wanted)} missing ones listed above, on different topics.\n"
        )
        try:
            known = {_clean(q.prompt).lower() for q in valid}
            more = [q for q in ask(wanted, extra) if _clean(q.prompt).lower() not in known]
        except LLMError as exc:
            logger.warning("quiz replacement request failed: %s", exc.code)
            more = []
        chosen, missing = pick([*valid, *more], slots)
    final = [q for q in chosen if q is not None]
    if len(final) < minimum:
        raise ApiError(
            502, "quiz_generation_failed", "We couldn't write enough questions for this project. Try again."
        )
    return final


# ---------------------------------------------------------------- storing


def _snippet(q: GeneratedQuestion, ctx: QuizContext) -> dict | None:
    ref = q.source_ref
    if ctx.kind != "code" or ref is None or not ctx.has_range(ref.path, ref.start_line, ref.end_line):
        return None
    start, end = ref.start_line, ref.end_line
    if end - start + 1 > SNIPPET_MAX_RANGE:
        if q.category != "code_reading":
            return None  # a whole-file range is context, not a snippet
        end = start + SNIPPET_MAX_LINES - 1
    end = min(end, start + SNIPPET_MAX_LINES - 1)
    ext = "." + ref.path.rsplit(".", 1)[-1].lower() if "." in ref.path else ""
    return {
        "path": ref.path, "start_line": start, "end_line": end,
        "code": ctx.excerpt(ref.path, start, end), "language": LANGUAGES.get(ext),
    }  # fmt: skip


def _source_ref(q: GeneratedQuestion, ctx: QuizContext) -> dict | None:
    ref = q.source_ref
    if ref is None:
        return None
    return {
        "path": ref.path,
        "start_line": ref.start_line if ctx.kind == "code" else None,
        "end_line": ref.end_line if ctx.kind == "code" else None,
        "section": ref.section if ctx.kind == "design" else None,
        "url": ctx.blob_url(ref.path, ref.start_line, ref.end_line),
    }


GRADING_CONTEXT_LINES = 60
GRADING_CONTEXT_CHARS = 1_500


def _grading_context(q: GeneratedQuestion, ctx: QuizContext) -> str | None:
    """What the grader may check an answer against: the cited lines, or the page text near the section."""
    ref = q.source_ref
    if ref is None:
        return None
    if ctx.kind == "code":
        return ctx.excerpt(ref.path, ref.start_line, ref.end_line, GRADING_CONTEXT_LINES)
    text = " ".join(ctx.page_text.split())
    at = text.lower().find(_clean(ref.section).lower())
    return text[max(0, at - 200) : at + GRADING_CONTEXT_CHARS] if at >= 0 else text[:GRADING_CONTEXT_CHARS]


def to_rows(
    questions: list[GeneratedQuestion], ctx: QuizContext, mode: str, quiz_id: str
) -> list[models.QuizQuestion]:
    rows = []
    for order, q in enumerate(questions, start=1):
        options, correct = [], None
        if q.type == "mcq":
            rng = random.Random(f"{quiz_id}:{order}")  # the key is not always "a"
            shuffled = list(q.options)
            rng.shuffle(shuffled)
            for label, option in zip("abcd", shuffled, strict=True):
                options.append({"id": label, "text": _clean(option.text)})
                if option.id == q.correct_choice_id:
                    correct = label
        limit = (MCQ_SECONDS if q.type == "mcq" else SHORT_SECONDS) if mode == "verify" else None
        rows.append(
            models.QuizQuestion(
                quiz_id=quiz_id,
                order=order,
                type=q.type,
                category=q.category,
                prompt=_clean(q.prompt),
                code_snippet=_snippet(q, ctx),
                options=options,
                hint=_clean(q.hint) or None,
                skill_ids=q.skill_ids,
                time_limit_s=limit,
                source_ref=_source_ref(q, ctx),
                correct_choice_id=correct,
                key_points=q.key_points,
                acceptable_alternatives=[_clean(a) for a in q.acceptable_alternatives if _clean(a)],
                model_answer=_clean(q.model_answer) or None,
                grading_context=_grading_context(q, ctx),
            )
        )
    return rows


# ---------------------------------------------------------------- the project and its material


def find_project(analysis: models.Analysis, project_id: str) -> tuple[ScoringInputs, ProjectInput]:
    if analysis.status != "done" or not analysis.signals:
        raise ApiError(409, "analysis_not_ready", "This analysis hasn't finished yet")
    inputs = ScoringInputs.model_validate(analysis.signals)
    project = next((p for p in inputs.projects if p.project_id == project_id), None)
    if project is None:
        raise not_found("Project")
    return inputs, project


def check_quizzable(project: ProjectInput) -> None:
    if project.kind == "design":
        ok = bool(project.url) and project.design is not None and project.design.readable
    else:
        signals = project.signals
        ok = (
            signals is not None
            and repo_from_url(project.url) is not None
            and not (signals.is_fork and signals.fork_authored_commits == 0)
        )
    if not ok:
        raise ApiError(
            422,
            "project_not_quizzable",
            "There isn't enough of your own work in this project to ask about yet.",
            {"project_id": project.project_id},
        )


def project_description(inputs: ScoringInputs, project: ProjectInput, analysis: models.Analysis) -> str:
    """The student's own words about the project: the matching resume entry, else the stored summary."""
    for entry in inputs.resume.projects:
        if slug(entry.title) == slug(project.title):
            return entry.description
    report = AnalysisReport.model_validate(analysis.report) if analysis.report else None
    audit = next((p for p in report.projects if p.project_id == project.project_id), None) if report else None
    return (audit.what_it_does or "") if audit else ""


def gather_context(project: ProjectInput, description: str, db: Session, deps: PipelineDeps) -> QuizContext:
    """Fetch what the questions are written from. Raises 502 `quiz_context_unavailable`."""
    try:
        if project.kind == "design":
            page_fetcher = deps.fetch_page or (lambda url, session, fresh: fetch_page(url, session))
            return build_design_context(
                project, page_fetcher(project.url, db, False), description=description
            )
        owner, repo = repo_from_url(project.url)
        factory = deps.github_client or (lambda session, fresh: GitHubClient(session, refresh=fresh))
        client = factory(db, False)
        tree = client.rest_get(f"/repos/{owner}/{repo}/git/trees/HEAD?recursive=1", missing_ok=True)
        entries = [
            TreeEntry(path=e["path"], size=e.get("size", 0))
            for e in (tree or {}).get("tree", [])
            if e["type"] == "blob"
        ]
        return build_code_context(
            project,
            entries,
            lambda paths: fetch_files(client, owner, repo, paths),
            description=description,
        )
    except ApiError as exc:
        if exc.code in ("github_not_found", "rate_limited", "github_unavailable", "github_not_configured"):
            raise ApiError(
                502, "quiz_context_unavailable", "We couldn't read this project right now. Try again shortly."
            ) from exc
        raise


def llm_error(exc: LLMError) -> ApiError:
    """LLM trouble as the contract's 429 (quota) or a clear 502/503."""
    if exc.code == "llm_unavailable":
        return ApiError(429, "llm_unavailable", "The AI service is busy right now. Try again in a minute.")
    if exc.code == "llm_not_configured":
        return ApiError(503, "llm_not_configured", exc.message)
    return ApiError(502, "quiz_generation_failed", "We couldn't write the questions this time. Try again.")


def create_quiz(
    db: Session, analysis: models.Analysis, body: QuizCreate, deps: PipelineDeps, *, now: datetime
) -> models.Quiz:
    inputs, project = find_project(analysis, body.project_id)
    check_quizzable(project)
    mode = body.mode.value
    prior = (
        select(func.count())
        .select_from(models.Quiz)
        .where(
            models.Quiz.profile_id == analysis.profile_id,
            models.Quiz.project_id == project.project_id,
            models.Quiz.mode == mode,
        )
    )
    attempt = 1 + db.scalar(prior)
    ctx = gather_context(project, project_description(inputs, project, analysis), db, deps)
    if ctx.kind == "code" and not ctx.files:
        raise ApiError(
            502, "quiz_context_unavailable", "We couldn't find readable source files in this project."
        )
    count = VERIFY_QUESTIONS if body.mode == QuizMode.verify else (body.question_count or PRACTICE_DEFAULT)
    slots = mix_for(mode, ctx.kind, count)
    try:
        questions = generate_questions(ctx, slots, mode, attempt, db, deps.providers)
    except LLMError as exc:
        raise llm_error(exc) from exc

    quiz = models.Quiz(
        analysis_id=analysis.id,
        profile_id=analysis.profile_id,
        project_id=project.project_id,
        project_title=project.title,
        project_url=project.url,
        kind=ctx.kind,
        mode=mode,
        attempt=attempt,
        created_at=now,
    )
    db.add(quiz)
    db.flush()
    quiz.questions = to_rows(questions, ctx, mode, quiz.id)
    db.commit()
    return quiz
