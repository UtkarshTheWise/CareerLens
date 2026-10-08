"""Truthful resume tailoring (docs/PIPELINE.md, P2). The model rewrites; Python decides what may stand.

A rewritten bullet is kept only if it adds no skill the student has not verified and no number that was
not already in the original bullet; otherwise the original stays. `original` always comes from the stored
resume, never from the model's reply. `numbers_without_evidence` and `skills_order` are computed here,
deterministically, with no LLM.
"""

import re

from sqlalchemy.orm import Session

from app import catalogue
from app.db import models
from app.errors import ApiError
from app.prompts import load_prompt
from app.schemas.api import AnalysisReport, EvidenceLevel, SkillClaim, TailoredBullet, TailoredResume
from app.schemas.llm import ResumeProfile, TailoredDraft
from app.services.cohorts import latest_done_analysis
from app.services.ingest import restore_pii, strip_pii
from app.services.llm import LLMError, Provider, generate_structured
from app.services.matching import resolve_skills
from app.services.quiz import llm_error

MAX_BULLETS = 12
MAX_BULLET_CHARS = 400
MAX_JOB_CHARS = 6_000
MIN_DESCRIPTION_CHARS = 40
VERIFIED = {EvidenceLevel.strong, EvidenceLevel.moderate}
_SEPARATOR = "\n=====BULLET=====\n"
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?%?")
_YEAR = re.compile(r"^(?:19|20)\d{2}$")


def numbers_in(text: str) -> list[str]:
    """Metric-like numbers in a text ("35%", "10,000", "3"), not calendar years, in order, unique."""
    found = [n.rstrip(",.") for n in _NUMBER.findall(text)]
    return list(dict.fromkeys(n for n in found if n and not _YEAR.match(n)))


def collect_bullets(resume: ResumeProfile) -> list[str]:
    """The student's own bullets: experience bullets, then project descriptions. Up to 12, no repeats."""
    raw = [b for exp in resume.experience for b in exp.bullets] + [p.description for p in resume.projects]
    cleaned = [" ".join(b.split())[:MAX_BULLET_CHARS] for b in raw if b and b.strip()]
    return list(dict.fromkeys(cleaned))[:MAX_BULLETS]


def verified_claims(report: AnalysisReport) -> list[SkillClaim]:
    return [c for c in report.claims if c.level in VERIFIED]


def facts_text(claims: list[SkillClaim]) -> str:
    lines = []
    for c in claims:
        ids = ", ".join(c.evidence_ids) or "none"
        lines.append(f"- {c.skill_name} ({c.level.value}): {c.reason} [evidence: {ids}]")
    return "\n".join(lines) or "(none)"


def check_rewrite(original: str, rewritten: str, allowed_skills: set[str]) -> str:
    """The rewrite if it is safe, else the original."""
    text = " ".join(rewritten.split())
    if not text or len(text) > MAX_BULLET_CHARS:
        return original
    if not set(numbers_in(text)) <= set(numbers_in(original)):
        return original  # a number the student never wrote
    seen = catalogue.find_skills_in_text(text)
    if not seen <= allowed_skills | catalogue.find_skills_in_text(original):
        return original  # a skill the student has no verified evidence for
    return text


def unsupported_numbers(bullets: list[str], facts: str) -> list[str]:
    """Numbers in the student's bullets that no verified fact mentions (listed, never removed)."""
    supported = set(numbers_in(facts))
    out: list[str] = []
    for bullet in bullets:
        out += [n for n in numbers_in(bullet) if n not in supported]
    return list(dict.fromkeys(out))


def skills_order(claims: list[SkillClaim], job_skill_ids: set[str]) -> list[str]:
    """Verified skills, the job's own first, strong before moderate, then by name."""
    ranked = sorted(
        claims,
        key=lambda c: (c.skill_id not in job_skill_ids, c.level != EvidenceLevel.strong, c.skill_name),
    )
    return [c.skill_name for c in ranked]


def tailor_resume(
    db: Session,
    application: models.Application,
    *,
    providers: list[Provider] | None = None,
) -> TailoredResume:
    description = (application.description or "").strip()
    if len(description) < MIN_DESCRIPTION_CHARS:
        raise ApiError(
            422, "no_description", "Add the job description to this application first, then tailor.",
            {"field": "description"},
        )  # fmt: skip
    analysis = latest_done_analysis(db, application.profile_id)
    if analysis is None or not analysis.signals:
        raise ApiError(409, "no_analysis", "Run an analysis before tailoring a resume")
    report = AnalysisReport.model_validate(analysis.report)
    resume = ResumeProfile.model_validate(analysis.signals["resume"])
    bullets = collect_bullets(resume)
    claims = verified_claims(report)
    facts = facts_text(claims)
    job_ids = set(resolve_skills([application.title])[0]) | catalogue.find_skills_in_text(description)
    order = skills_order(claims, job_ids)
    if not bullets:
        return TailoredResume(bullets=[], numbers_without_evidence=[], skills_order=order)

    name = application.profile.name
    stripped = strip_pii(_SEPARATOR.join(bullets), known_names=[name] if name else [], header_name=False)
    clean_bullets = stripped.text.split(_SEPARATOR)
    job_text = strip_pii(description[:MAX_JOB_CHARS], header_name=False).text
    prompt = load_prompt("tailor_resume")
    user = prompt.user(
        title=application.title,
        company=application.company,
        description=job_text,
        facts=facts,
        bullets="\n".join(f"b{n}: {text}" for n, text in enumerate(clean_bullets, start=1)),
    )
    try:
        draft = generate_structured(
            TailoredDraft, prompt.system, user, tier="smart", db=db, providers=providers
        )
    except LLMError as exc:
        raise llm_error(exc) from exc

    known = {eid for c in claims for eid in c.evidence_ids} | {e.id for e in report.evidence}
    allowed_skills = {c.skill_id for c in claims}
    by_id = {d.bullet_id: d for d in draft.bullets}
    out = []
    for n, original in enumerate(bullets, start=1):
        d = by_id.get(f"b{n}")
        rewritten = original
        evidence: list[str] = []
        if d is not None:
            candidate = restore_pii(d.rewritten, stripped.mapping)
            rewritten = check_rewrite(original, candidate, allowed_skills)
            if rewritten != original:
                evidence = [e for e in dict.fromkeys(d.evidence_ids) if e in known]
        out.append(TailoredBullet(original=original, rewritten=rewritten, evidence_ids=evidence))
    return TailoredResume(
        bullets=out, numbers_without_evidence=unsupported_numbers(bullets, facts), skills_order=order
    )
