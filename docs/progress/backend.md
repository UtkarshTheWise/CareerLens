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
- **Last updated:** 2026-10-07 16:00 IST by Claude Code (Opus 5.5)
- **Current task:** B3 done (live LLM call not verified: no API keys in `.env`). Next: B4 (GitHub collector, detectors).
- **State:** done   <!-- not started | in progress | blocked | done -->
- **Last green checks:** 2026-10-07 15:58 IST, from `apps/api`: `uv run pytest -q` (110 passed) · `uv run ruff check .` · `uv run python scripts/check_contract.py --only-implemented` (8/29 routed, 0 mismatches)

## Resume here (exact next step)
<!-- Precise enough for a model with zero context: file, function, what's left, the next command to run. -->
1. FIRST, once a key exists: put `GEMINI_API_KEY` and/or `GROQ_API_KEY` in `apps/api/.env`, then `cd apps/api && uv run pytest -m live -q`. It makes one real `extract_resume` call on the synthetic fixture resume. If Gemini rejects the request (HTTP 400), look at `GeminiProvider.complete` in `app/services/llm.py` (the `response_json_schema` config) and the model ids in `.env`.
2. Start B4: paste its prompt from PROMPTS.md. New files: `app/services/github.py`, `app/services/detectors.py`, `scripts/record_github.py`, `tests/fixtures/github/`. B4 needs `GITHUB_TOKEN` in `.env` to record fixtures. Cache GitHub responses in the `cache` table (`CacheEntry`, kind `github`, 24 h via `expires_at`).
3. Detectors read `catalogue.load_skills()` (`SkillDef.detectors`); `load_tutorial_names()` and `load_readme_templates()` feed the rule flags.
4. After any route or schema change: `cd apps/api && uv run python scripts/check_contract.py --only-implemented`.

## Task board
<!-- status: todo | doing | done | blocked · commit = short sha of the commit that finished it -->
| Id | Task | Status | Commit | Notes |
|---|---|---|---|---|
| B1 | Scaffold FastAPI, config, DB, errors, /health, /v1/roles, /v1/me, check_contract.py | done | 35c1be2 | all contract schemas already in `app/schemas/api.py` |
| B2 | Catalogues: skills.yaml, roles.yaml, resources.yaml + loaders/tests | done | e67462c | 63 skills, 7 roles, 130 resources; all links checked live |
| B3 | Ingest, PII stripping, LLM gateway, resume extraction | done | SHA_B3 | live LLM call unverified (no keys); profile CRUD + upload real |
| B4 | GitHub collector, detectors, repo signals, rule flags | todo | | |
| B5 | scoring.py + what-if + unit tests | todo | | |
| B6 | Pipeline, analyses endpoints, judging, roadmap planner, role-fit | todo | | also `PATCH /v1/analyses/{id}/roadmap/{milestone_id}` (added at freeze) |
| B7 | Jobs match, applications, cohorts, seed_demo.py | todo | | |
| B9 | Project Understanding Check (quiz) | todo | | also `GET /v1/quizzes/{id}/result`; 429 detail key is `retake_available_at`, not `retry_at` as the B9 prompt says |
| B8 | Hardening, contract check green, deploy, keep-alive | todo | | Supabase JWT verification lands here |

## In-progress detail
- **Files touched, not finished:** none
- **What works right now:** `GET /health`, `GET /v1/roles` (7 real roles), `GET /v1/me`, profile create/get/patch/delete, document upload (PDF/DOCX -> text) (demo profile, created on first call under `DEV_AUTH=1`); every error in the contract `Error` shape (404/405/422/500 + `ApiError`); CORS for `CORS_ORIGINS` and `chrome-extension://*`; tables created at startup.
- **Stubbed / fake (search `TODO(progress)`):**
  - `app/deps.py:get_auth_subject`: with `DEV_AUTH=0` every request gets 401 (no Supabase JWT verification yet) → B8.
- **Known failing tests / checks:** none offline. `pytest -m live` fails with `llm_unavailable` until an LLM key is in `.env` (or Ollama is running). `check_contract.py` without `--only-implemented` exits 1 by design until all 29 operations are routed.

## Decisions made (one line each, append)
- Tables are created with `Base.metadata.create_all` at startup; no Alembic for the prototype.
- Ids are UUID strings (`String(36)`) so the same models run on SQLite and Postgres.
- `FastAPI(separate_input_output_schemas=False)`: one OpenAPI schema per model, named as in the contract.
- In `schemas/api.py` a field is required iff it has no default; inline contract objects get helper models (`RoleSkill`, `ScoreReason`, ...), whose names are not part of the contract.
- `check_contract.py` also checks models that no route uses yet (it adds every model in `app/schemas/api.py` to the app spec), plus request bodies, operationIds and basic JSON types.
- Routers pass `operation_id=` from the contract and `responses=ERROR_RESPONSES`; non-200 success codes must be set with `status_code=` or the check fails.
- Validation errors return field locations and messages only, never the submitted values.
- roles.yaml lists `{skill, importance}` only; the loader fills `skill_name` from skills.yaml. `RoleDef` (internal) adds `weights`; the API still returns the contract `Role`.
- `read_catalogue()` reports every catalogue problem at once and runs in the app lifespan, so the server won't start on bad data.
- `readme_templates.txt` uses `//` for comments because real markers start with `#`.
- LLM gateway: `generate_structured(schema, system, user, tier, db=...)` in `app/services/llm.py`; providers are injectable (`providers=[...]`) so tests use fakes. Cache key uses the tier's Gemini model name even when Groq/Ollama answered, so reruns hit the cache.
- A 4xx other than 429 from a provider raises `LLMError(llm_request_rejected)` instead of falling back: it means our request is wrong.
- Documents store raw text; PII is stripped only when building an LLM prompt (`strip_pii`) and restored in the result (`restore_pii`). The cache therefore holds placeholders, not real links.
- Prompts are `app/prompts/<name>.md` with `## System` / `## User`; load with `load_prompt(name)`.
- LLM schemas (`app/schemas/llm.py`) must stay free of free-form dicts: Groq strict mode needs closed objects.
- Datetime columns use `UtcDateTime` (SQLite returns naive values otherwise, and the API would drop the `Z`).
- Per-project quiz understanding will live in `profiles.project_understanding` (JSON keyed by repo/portfolio URL).

## Gotchas learned (one line each, append)
- `.env` currently configures only Ollama (`OLLAMA_URL` came from `.env.example`); `/health` reports `llm_provider: ollama` even if Ollama isn't running. Health should probe it in B8.
- uvicorn does not show the app's INFO logs (no logging config yet): stage timings are invisible until B8 adds structured logging.
- PDF fixtures are hand-built ASCII; `tests/fixtures/.gitattributes` marks them binary so git doesn't rewrite line endings and break them.
- New fixtures: `uv run python tests/fixtures/make_fixtures.py`.
- `scripts/check_resource_urls.py` is live and manual; w3.org and tableau.com answer 403 to scripts (reported as `blocked`, not a failure).
- Skills with `detectors: {}` are intentional (no repo footprint); evidence for them comes from experience and portfolio items.
- `uv` lives in `~/.local/bin`; in Git Bash run `export PATH="$HOME/.local/bin:$PATH"` first if `uv` isn't found.
- Tests set `DATABASE_URL=sqlite:///:memory:` and `DEV_AUTH=1` in `tests/conftest.py` before importing the app, so they never read the real `.env` database.
- `Settings.cors_origins` is a comma-separated string (a `list[str]` field would make pydantic-settings expect JSON in `.env`); use `settings.cors_origin_list`.
- Starlette prints a deprecation warning about `httpx` in `TestClient`; harmless.

## Blocked on / open questions
- none

## Environment
- `apps/api/.env` keys set: GEMINI ☐ GROQ ☐ GITHUB_TOKEN ☐ DATABASE_URL ☐ (never paste values here; not checked by the agent, the file is deny-listed)
- Run: `cd apps/api && uv sync && uv run fastapi dev app/main.py` → :8000
- Tooling on this machine: uv 0.12.23 (installed 2026-10-07), Python 3.12.15 via uv (`apps/api/.python-version`), Node 22.16.0, pnpm 10.12.3
- Gemini model IDs confirmed in AI Studio: —
- `apps/api/.env.example` lists every key; it defaults `DATABASE_URL` to `sqlite:///./dev.db`
- Contract frozen at v0.2.0; lint with `npx @redocly/cli lint contracts/openapi.yaml` (config in `redocly.yaml`). Freeze changes are listed in `docs/handoff/integration.md`.
