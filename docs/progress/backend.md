# Progress — Backend track

<!--
Living snapshot for context hand-off. ANY agent/model continuing this track reads this first.
Overwrite sections to reflect the truth NOW; don't append history (history and messages go in docs/handoff/backend.md).
Update after every meaningful step, not just at the end: usage limits cut sessions off without warning.
Keep under ~150 lines. Commit it together with the code it describes.
-->

## Status
- **Track:** backend · **Owns:** `apps/api/`, `data/`
- **Branch / worktree:** `backend/claude` · `../careerlens-api`
- **Last updated:** YYYY-MM-DD HH:MM IST by <agent> (<model>)
- **Current task:** — 
- **State:** not started   <!-- not started | in progress | blocked | done -->
- **Last green checks:** — 

## Resume here (exact next step)
<!-- Precise enough for a model with zero context: file, function, what's left, the next command to run. -->
1. Start B1: run its prompt from PROMPTS.md.

## Task board
<!-- status: todo | doing | done | blocked · commit = short sha of the commit that finished it -->
| Id | Task | Status | Commit | Notes |
|---|---|---|---|---|
| B1 | Scaffold FastAPI, config, DB, errors, /health, /v1/roles, /v1/me, check_contract.py | todo | | |
| B2 | Catalogues: skills.yaml, roles.yaml, resources.yaml + loaders/tests | todo | | |
| B3 | Ingest, PII stripping, LLM gateway, resume extraction | todo | | |
| B4 | GitHub collector, detectors, repo signals, rule flags | todo | | |
| B5 | scoring.py + what-if + unit tests | todo | | |
| B6 | Pipeline, analyses endpoints, judging, roadmap planner, role-fit | todo | | |
| B7 | Jobs match, applications, cohorts, seed_demo.py | todo | | |
| B9 | Project Understanding Check (quiz) | todo | | |
| B8 | Hardening, contract check green, deploy, keep-alive | todo | | |

## In-progress detail
- **Files touched, not finished:** —
- **What works right now:** —
- **Stubbed / fake (search `TODO(progress)`):** —
- **Known failing tests / checks:** —

## Decisions made (one line each, append)
- 

## Gotchas learned (one line each, append)
- 

## Blocked on / open questions
- 

## Environment
- `apps/api/.env` keys set: GEMINI ☐ GROQ ☐ GITHUB_TOKEN ☐ DATABASE_URL ☐ (never paste values here)
- Run: `uv run fastapi dev app/main.py` → :8000
- Gemini model IDs confirmed in AI Studio: —
