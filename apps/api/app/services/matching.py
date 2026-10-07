"""Job matching (docs/PIPELINE.md, "Job page extraction fallback").

`normalize_posting` fills a posting's skill lists (from the LLM extractor when the page had none) and
`match` is pure and deterministic: keyword_match is how many of the posting's skills are on the profile,
evidence_match weighs each by how well it is backed (SCORING.md credits). Neither calls GitHub.
"""

import logging
from datetime import date

from sqlalchemy.orm import Session

from app import catalogue
from app.prompts import load_prompt
from app.schemas.api import EvidenceLevel, JobMatch, JobPosting, MatchedSkill
from app.schemas.llm import JobPostingExtract
from app.services import scoring
from app.services.ingest import strip_pii
from app.services.llm import LLMError, Provider, generate_structured
from app.services.scoring_inputs import ScoringInputs

logger = logging.getLogger("careerlens.matching")

MAX_EXTRACT_CHARS = 12_000
UNBACKED = {EvidenceLevel.weak, EvidenceLevel.unverified}


def resolve_skills(names: list[str]) -> tuple[list[str], list[str]]:
    """Catalogue skill ids for skill strings from a posting, and the strings that matched nothing.

    A string can name several skills ("Docker and Kubernetes"), so unknown exact names are scanned as text.
    """
    ids: list[str] = []
    unknown: list[str] = []
    for raw in names:
        raw = raw.strip()
        if not raw:
            continue
        sid = catalogue.normalize_skill(raw)
        found = [sid] if sid else sorted(catalogue.find_skills_in_text(raw))
        if not found:
            unknown.append(raw)
        ids += [s for s in found if s not in ids]
    return ids, list(dict.fromkeys(unknown))


def _name(skill_id: str) -> str:
    skill = catalogue.get_skill(skill_id)
    return skill.name if skill else skill_id


def _parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def normalize_posting(
    posting: JobPosting, db: Session, *, providers: list[Provider] | None = None
) -> tuple[JobPosting, list[str]]:
    """The posting with skills extracted if it had none (or came from the LLM), and any notes.

    The page text is PII-stripped before the call. If the extractor is unavailable the catalogue is
    scanned against the description instead, so matching still works.
    """
    notes: list[str] = []
    if posting.source != "llm" and posting.required_skills:
        return posting, notes
    update: dict = {}
    try:
        clean = strip_pii(posting.description[:MAX_EXTRACT_CHARS], header_name=False).text
        prompt = load_prompt("extract_job")
        extract = generate_structured(
            JobPostingExtract, prompt.system, prompt.user(description=clean), tier="fast", db=db,
            providers=providers,
        )  # fmt: skip
        update = {
            "required_skills": extract.required_skills,
            "nice_to_have": extract.nice_to_have,
            "company": posting.company or extract.company,
            "location": posting.location or extract.location,
            "deadline": posting.deadline or _parse_date(extract.deadline),
        }
    except LLMError as exc:
        logger.warning("job extraction unavailable: %s", exc.code)
        found = sorted(catalogue.find_skills_in_text(posting.description))
        update = {"required_skills": [_name(s) for s in found]}
        notes.append(
            "The posting's skills were read by scanning the text because the AI reader was unavailable."
        )
    return posting.model_copy(update=update), notes


def _list_names(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def match(inputs: ScoringInputs, posting: JobPosting, notes: list[str] | None = None) -> JobMatch:
    """Keyword and evidence-backed match of the student's profile against a posting's skills."""
    required, unknown_required = resolve_skills(posting.required_skills)
    nice, unknown_nice = resolve_skills(posting.nice_to_have)
    nice = [s for s in nice if s not in required]
    unknown = [*unknown_required, *[u for u in unknown_nice if u not in unknown_required]]
    wanted, kind = (required, "required") if required else (nice, "preferred")

    normalized = posting.model_copy(
        update={
            "required_skills": [*(_name(s) for s in required), *unknown_required],
            "nice_to_have": [*(_name(s) for s in nice), *unknown_nice],
        }
    )
    extra = list(notes or [])
    if unknown:
        count = f"{len(unknown)} skill{'s' if len(unknown) != 1 else ''} named in the posting"
        names = _list_names(unknown[:5])
        extra.append(f"{count} ({names}) aren't in the skill catalogue and weren't counted.")

    if not wanted:
        empty = "This posting lists no recognisable skills, so there is nothing to match yet."
        summary = " ".join([empty, *extra])
        return JobMatch(
            keyword_match=0, evidence_match=0, matched=[], missing=[], unverified=[],
            summary=summary, normalized_posting=normalized,
        )  # fmt: skip

    levels = scoring.skill_levels(inputs, wanted)
    matched = [MatchedSkill(skill_id=s, skill_name=_name(s), level=levels[s][0]) for s in wanted
               if levels[s][0] != EvidenceLevel.missing]  # fmt: skip
    missing = [_name(s) for s in wanted if levels[s][0] == EvidenceLevel.missing]
    unverified = [m.skill_name for m in matched if m.level in UNBACKED]
    backed = len(matched) - len(unverified)
    total = len(wanted)
    keyword = round(100 * len(matched) / total, 1)
    evidence = round(100 * sum(scoring.CREDIT[m.level.value] for m in matched) / total, 1)

    parts = [
        f"You have {len(matched)} of the {total} {kind} skill{'s' if total != 1 else ''} on your profile"
        f" and {backed} {'is' if backed == 1 else 'are'} backed by your own work."
    ]
    if unverified:
        verb = "is" if len(unverified) == 1 else "are"
        parts.append(f"{_list_names(unverified)} {verb} claimed without evidence yet.")
    if missing:
        verb = "is" if len(missing) == 1 else "are"
        parts.append(f"{_list_names(missing)} {verb} not on your profile.")
    hidden = [m.skill_name for m in matched if not levels[m.skill_id][1] and m.level not in UNBACKED]
    if hidden:
        verb = "appears" if len(hidden) == 1 else "appear"
        parts.append(f"{_list_names(hidden)} {verb} in your repositories but not on your resume.")
    return JobMatch(
        keyword_match=keyword, evidence_match=evidence, matched=matched, missing=missing,
        unverified=unverified, summary=" ".join([*parts, *extra]), normalized_posting=normalized,
    )  # fmt: skip
