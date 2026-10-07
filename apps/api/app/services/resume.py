"""Stage 2 (docs/PIPELINE.md): resume + LinkedIn text -> ResumeProfile via the LLM gateway."""

from sqlalchemy.orm import Session

from app.db import models
from app.errors import ApiError
from app.prompts import load_prompt
from app.schemas.llm import ResumeProfile
from app.services.ingest import restore_pii, strip_pii
from app.services.llm import Provider, generate_structured

# Keeps the fast-tier call inside the free-tier token budget; a 2-page resume is ~6k chars.
MAX_RESUME_CHARS = 20_000
MAX_LINKEDIN_CHARS = 10_000
_SEPARATOR = "\n=====LINKEDIN=====\n"


def _document_text(profile: models.Profile, kind: str) -> str:
    docs = sorted((d for d in profile.documents if d.kind == kind), key=lambda d: d.created_at)
    return docs[-1].text if docs else ""


def extract_resume(
    profile: models.Profile,
    db: Session,
    *,
    force_refresh: bool = False,
    providers: list[Provider] | None = None,
) -> ResumeProfile:
    """Parse the profile's resume. PII is stripped before the call and restored in the result."""
    resume_text = _document_text(profile, "resume")
    if not resume_text:
        raise ApiError(409, "no_resume", "Upload a resume before starting an analysis")
    linkedin_text = "\n\n".join(
        t for t in (_document_text(profile, "linkedin"), profile.linkedin_text or "") if t
    )

    # Strip both texts in one pass so a placeholder means the same value in each of them.
    stripped = strip_pii(
        resume_text[:MAX_RESUME_CHARS] + _SEPARATOR + linkedin_text[:MAX_LINKEDIN_CHARS],
        known_names=[profile.name] if profile.name else [],
    )
    clean_resume, _, clean_linkedin = stripped.text.partition(_SEPARATOR)

    prompt = load_prompt("extract_resume")
    result = generate_structured(
        ResumeProfile,
        prompt.system,
        prompt.user(resume_text=clean_resume, linkedin_text=clean_linkedin),
        tier="fast",
        db=db,
        force_refresh=force_refresh,
        providers=providers,
    )
    # Project links come back as real URLs so they can be matched to GitHub repos later.
    restored = restore_pii(result, stripped.mapping)
    # The page count is measured from the file, not guessed by the model.
    resume_doc = max((d for d in profile.documents if d.kind == "resume"), key=lambda d: d.created_at)
    restored.page_count_hint = resume_doc.page_count or restored.page_count_hint
    return restored
