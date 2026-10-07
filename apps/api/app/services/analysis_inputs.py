"""Stages 5-6 glue (docs/PIPELINE.md): match resume projects to repos, run the LLM judges, raise the
`vague_description` / `claim_mismatch` flags and build the `ProjectInput`s that scoring consumes.

Everything sent to a model goes through `strip_pii` first.
"""

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app import catalogue
from app.catalogue import RoleDef
from app.prompts import load_prompt
from app.schemas.api import Understanding
from app.schemas.llm import (
    DesignJudgement,
    JudgementIssue,
    ProjectJudgement,
    ResumeProfile,
    ResumeProject,
)
from app.services.detectors import RepoAnalysis
from app.services.github import GithubSnapshot, RepoData
from app.services.ingest import strip_pii
from app.services.llm import Provider, generate_structured
from app.services.portfolio import PageText
from app.services.scoring import project_id_for
from app.services.scoring_inputs import DesignInput, FlagInput, ProjectInput

logger = logging.getLogger("careerlens.analysis")

MAX_JUDGED = 6  # docs/PIPELINE.md stage 5: one call per project, at most six
NAME_SIMILARITY = 0.85
README_EXCERPT_CHARS = 1500

# Severities for the two flags B6 raises (B4's live in detectors.FLAG_SEVERITY).
EXTRA_SEVERITY = {"vague_description": "low", "claim_mismatch": "medium"}

_GITHUB_REPO = re.compile(r"github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9._-]+)", re.IGNORECASE)


@dataclass
class ProjectText:
    """LLM-written report text for one project (never used for scoring except through the flags)."""

    what_it_does: str | None = None
    honest_rewrite: str | None = None
    issues: list[JudgementIssue] = field(default_factory=list)


@dataclass
class DesignItem:
    url: str
    page: PageText
    design: DesignInput
    issues: list[JudgementIssue] = field(default_factory=list)


# ---------------------------------------------------------------- resume project <-> repo matching


def _repo_key(url: str | None) -> str | None:
    match = _GITHUB_REPO.search(url or "")
    return f"{match.group(1)}/{match.group(2).removesuffix('.git')}".lower() if match else None


def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def match_resume_projects(resume: ResumeProfile, repos: Sequence[RepoData]) -> dict[str, ResumeProject]:
    """repo name -> the resume project describing it. By repo URL first, then by name; one-to-one."""
    matched: dict[str, ResumeProject] = {}
    used: set[int] = set()
    by_key = {_repo_key(r.url): r for r in repos}
    for i, project in enumerate(resume.projects):
        for link in project.links:
            repo = by_key.get(_repo_key(link))
            if repo is not None and repo.name not in matched:
                matched[repo.name] = project
                used.add(i)
                break

    scored = []
    for i, project in enumerate(resume.projects):
        if i in used:
            continue
        for repo in repos:
            if repo.name in matched:
                continue
            a, b = _norm_name(project.title), _norm_name(repo.name)
            if a and b:
                ratio = 1.0 if a == b else SequenceMatcher(None, a, b).ratio()
                if ratio >= NAME_SIMILARITY:
                    scored.append((ratio, i, repo.name))
    for _ratio, i, name in sorted(scored, key=lambda t: (-t[0], t[1], t[2])):
        if i not in used and name not in matched:
            matched[name] = resume.projects[i]
            used.add(i)
    return matched


def claimed_skill_ids(project: ResumeProject) -> list[str]:
    found = {catalogue.normalize_skill(t) for t in project.mentioned_technologies if t}
    found |= catalogue.find_skills_in_text(project.description)
    return sorted(s for s in found if s and catalogue.get_skill(s) is not None)


# ---------------------------------------------------------------- choosing what the LLM reviews


def _relevance(analysis: RepoAnalysis, role: RoleDef) -> int:
    importance = {rs.skill_id: rs.importance for rs in role.skills}
    return sum(importance.get(s, 0) for s in set(analysis.skills) | set(analysis.language_skills))


def _untouched_fork(repo: RepoData) -> bool:
    return repo.is_fork and repo.authored_since_created == 0


def select_for_review(
    snapshot: GithubSnapshot,
    analyses: dict[str, RepoAnalysis],
    matched: dict[str, ResumeProject],
    role: RoleDef,
) -> list[str]:
    """Up to six repos: the ones on the resume first, then the most relevant to the role."""
    candidates = [r for r in snapshot.repos if r.name in analyses and not _untouched_fork(r)]
    candidates.sort(key=lambda r: (r.name not in matched, -_relevance(analyses[r.name], role), r.name))
    return [r.name for r in candidates[:MAX_JUDGED]]


# ---------------------------------------------------------------- the judges


def _clean(text: str, names: list[str]) -> str:
    return strip_pii(text or "", known_names=names, header_name=False).text


def judge_project(
    repo: RepoData,
    analysis: RepoAnalysis,
    resume_project: ResumeProject | None,
    role: RoleDef,
    *,
    student_name: str,
    db: Session,
    providers: list[Provider] | None,
    refresh: bool,
) -> ProjectJudgement:
    names = [student_name] if student_name else []
    description = (
        resume_project.description if resume_project else repo.description
    ) or "(no description written)"
    claimed = resume_project.mentioned_technologies if resume_project else []
    s = analysis.signals
    prompt = load_prompt("judge_project")
    user = prompt.user(
        role_name=role.name,
        project_description=_clean(description, names),
        claimed_technologies=", ".join(claimed) or "(none listed)",
        detected_skills=", ".join(
            sorted(catalogue.get_skill(k).name for k in analysis.skills if catalogue.get_skill(k))
        )
        or "(none detected)",
        authored_commits=str(s.authored_commits),
        total_commits=str(s.total_commits),
        span_weeks=f"{s.active_span_weeks:g}",
        has_tests="yes" if s.has_tests else "no",
        has_ci="yes" if s.has_ci else "no",
        homepage="yes" if s.has_demo_url else "none",  # the URL itself can contain a username
        license=repo.license or "none",
        rule_flags=", ".join(f.code for f in analysis.flags) or "none",
        readme_excerpt=_clean(repo.readme[:README_EXCERPT_CHARS], names) or "(no README)",
    )
    return generate_structured(
        ProjectJudgement, prompt.system, user, tier="smart", db=db, force_refresh=refresh, providers=providers
    )


def judge_design_item(
    page: PageText,
    role: RoleDef,
    resume: ResumeProfile,
    *,
    student_name: str,
    db: Session,
    providers: list[Provider] | None,
    refresh: bool,
) -> DesignItem:
    if not page.readable:
        return DesignItem(page.url, page, DesignInput(readable=False))
    names = [student_name] if student_name else []
    claimed_tools = sorted(
        {
            sk.name
            for raw in resume.skills
            if (sid := catalogue.normalize_skill(raw))
            and (sk := catalogue.get_skill(sid))
            and sk.category == "design"
        }
    )
    prompt = load_prompt("judge_design")
    user = prompt.user(
        role_name=role.name,
        url="(link removed)",
        og_title=_clean(page.title, names) or "(none)",
        og_description=_clean(page.description, names) or "(none)",
        claimed_tools=", ".join(claimed_tools) or "(none listed)",
        page_text=_clean(page.text, names),
    )
    judged = generate_structured(
        DesignJudgement, prompt.system, user, tier="smart", db=db, force_refresh=refresh, providers=providers
    )
    design = DesignInput(
        readable=judged.readable,
        problem_statement=judged.problem_statement,
        process_evidence=judged.process_evidence,
        outcome_or_metrics=judged.outcome_or_metrics,
        tool_evidence=judged.tool_evidence,
        presentation=judged.presentation,
        tools_seen=judged.tools_seen,
    )
    return DesignItem(page.url, page, design, judged.issues)


# ---------------------------------------------------------------- flags from the judgement


def _mismatched_claims(judged: ProjectJudgement, claimed: set[str], detected: set[str]) -> list[str]:
    """Skills the model could not see AND no detector found, among those the student claims."""
    unsupported: set[str] = set()
    for claim in judged.unsupported_claims:
        sid = catalogue.normalize_skill(claim)
        unsupported |= {sid} if sid else catalogue.find_skills_in_text(claim)
    return sorted(unsupported & claimed - detected)


def judgement_flags(judged: ProjectJudgement, claimed: set[str], detected: set[str]) -> list[FlagInput]:
    flags = []
    if judged.specificity <= 1 and not judged.has_metric:
        flags.append(
            FlagInput(
                code="vague_description",
                severity="low",
                reason="The description doesn't yet say how the project works or what it achieved.",
                fix="Add one number (latency, users, accuracy) and one sentence on how it works.",
            )
        )
    mismatched = _mismatched_claims(judged, claimed, detected)
    if mismatched:
        names = ", ".join(catalogue.get_skill(s).name for s in mismatched)
        flags.append(
            FlagInput(
                code="claim_mismatch",
                severity="medium",
                reason=f"The description names {names}, but no code for it was found in the repository.",
                fix="Either remove the claim or link the code that uses it.",
            )
        )
    return flags


# ---------------------------------------------------------------- ProjectInput assembly


def carry_understanding(
    url: str | None, stored: dict[str, Any]
) -> tuple[Understanding, list[str], str | None]:
    """Latest verify result for a project, from `profiles.project_understanding` (keyed by URL)."""
    entry = stored.get(url or "")
    if not isinstance(entry, dict):
        return Understanding.not_taken, [], None
    try:
        understanding = Understanding(entry.get("understanding", "not_taken"))
    except ValueError:
        understanding = Understanding.not_taken
    return understanding, list(entry.get("covered_skill_ids", [])), entry.get("quiz_id")


def build_project_inputs(
    snapshot: GithubSnapshot | None,
    analyses: dict[str, RepoAnalysis],
    matched: dict[str, ResumeProject],
    judgements: dict[str, ProjectJudgement],
    design_items: list[DesignItem],
    stored_understanding: dict[str, Any],
) -> tuple[list[ProjectInput], dict[str, ProjectText]]:
    projects: list[ProjectInput] = []
    texts: dict[str, ProjectText] = {}
    for repo in snapshot.repos if snapshot else []:
        analysis = analyses.get(repo.name)
        if analysis is None:
            continue
        pid = project_id_for(repo.name)
        resume_project = matched.get(repo.name)
        claimed = claimed_skill_ids(resume_project) if resume_project else []
        flags = [
            FlagInput(code=f.code, severity=f.severity, reason=f.reason, fix=f.fix) for f in analysis.flags
        ]
        judged = judgements.get(repo.name)
        if judged is not None:
            flags += judgement_flags(
                judged, set(claimed), set(analysis.skills) | set(analysis.language_skills)
            )
            texts[pid] = ProjectText(judged.what_it_does, judged.honest_rewrite, list(judged.issues))
        understanding, covered, quiz_id = carry_understanding(repo.url, stored_understanding)
        projects.append(
            ProjectInput(
                project_id=pid,
                title=repo.name,
                url=repo.url,
                demo_url=repo.homepage,
                signals=analysis.signals,
                skills=analysis.skills,
                language_skills=analysis.language_skills,
                claimed_skill_ids=claimed,
                flags=flags,
                understanding=understanding,
                covered_skill_ids=covered,
                latest_quiz_id=quiz_id,
            )
        )

    taken = {p.project_id for p in projects}
    for item in design_items:
        title = item.page.title or urlsplit(item.url).hostname or "Portfolio item"
        pid = base = project_id_for(title)
        n = 2
        while pid in taken:
            pid, n = f"{base}-{n}", n + 1
        taken.add(pid)
        understanding, covered, quiz_id = carry_understanding(item.url, stored_understanding)
        projects.append(
            ProjectInput(
                project_id=pid,
                title=title,
                kind="design",
                url=item.url,
                design=item.design,
                understanding=understanding,
                covered_skill_ids=covered,
                latest_quiz_id=quiz_id,
            )
        )
        if item.issues:
            texts[pid] = ProjectText(issues=list(item.issues))
    return projects, texts
