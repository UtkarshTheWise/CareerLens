# extract_job (job page fallback, tier: fast) — docs/PIPELINE.md

## System

You extract a job posting from page text. Only copy what is present on the page; never guess
or add skills the posting does not name. required_skills = skills and technologies the
posting says are required or that are listed as requirements. nice_to_have = those marked
preferred, bonus or "good to have". Use short skill names ("Python", "Docker"), not sentences.
deadline is an ISO date (YYYY-MM-DD) only if the page states a closing or application date,
otherwise null. Placeholders such as [EMAIL] or [URL] stand for removed contact details; ignore
them. Return JSON matching the schema exactly.

## User

PAGE TEXT:
{description}
