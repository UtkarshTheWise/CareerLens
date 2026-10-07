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
- **Last updated:** 2026-10-07 15:20 IST by Claude Code (Opus 5.5)
- **Current task:** B2 (catalogues): built and tested, wrap-up left (stopped at a usage limit).
- **State:** in progress   <!-- not started | in progress | blocked | done -->
- **Last green checks:** 2026-10-07 14:25 IST, from `apps/api`: `uv run pytest -q` (45 passed, with B2) · `uv run ruff check .` · `uv run python scripts/check_contract.py --only-implemented` (3/29 routed, 0 mismatches)

## Resume here (exact next step)
<!-- Precise enough for a model with zero context: file, function, what's left, the next command to run. -->
1. `cd apps/api && uv run python scripts/check_resource_urls.py`. Last run: 127 ok, 2 blocked (w3.org WAI, tableau.com: bot-blocked, open in a browser), 1 failed. The failed one (`design-systems-storybook`) was repointed to `https://storybook.js.org/tutorials/` and NOT re-checked: confirm it answers, else replace it with another free design-systems resource.
2. Optional tidy in `data/resources.yaml`: the script printed `moved` for ~15 URLs (redirects, all still working); update them to the final URLs it printed, e.g. `interaction-design.org/literature/topics/...` -> `ixdf.org/literature/topics/...`.
3. Run `uv run pytest -q && uv run ruff check . && uv run python scripts/check_contract.py --only-implemented`, start the server and `curl /v1/roles` (expect 7 roles).
4. Append the B2 entry to `docs/handoff/backend.md` (catalogue contents, URL check result, note that skills with `detectors: {}` are evidenced by experience/portfolio, not an error for B4/B5).
5. Mark B2 `done` with its sha here, commit `feat(data): skill, role and resource catalogues with validated loaders`, push. Then B3.

## Task board
<!-- status: todo | doing | done | blocked · commit = short sha of the commit that finished it -->
| Id | Task | Status | Commit | Notes |
|---|---|---|---|---|
| B1 | Scaffold FastAPI, config, DB, errors, /health, /v1/roles, /v1/me, check_contract.py | done | 35c1be2 | all contract schemas already in `app/schemas/api.py` |
| B2 | Catalogues: skills.yaml, roles.yaml, resources.yaml + loaders/tests | doing | wip commit | 63 skills, 7 roles, 130 resources, name lists, loaders + 29 tests done; wrap-up steps in Resume here |
| B3 | Ingest, PII stripping, LLM gateway, resume extraction | todo | | |
| B4 | GitHub collector, detectors, repo signals, rule flags | todo | | |
| B5 | scoring.py + what-if + unit tests | todo | | |
| B6 | Pipeline, analyses endpoints, judging, roadmap planner, role-fit | todo | | also `PATCH /v1/analyses/{id}/roadmap/{milestone_id}` (added at freeze) |
| B7 | Jobs match, applications, cohorts, seed_demo.py | todo | | |
| B9 | Project Understanding Check (quiz) | todo | | also `GET /v1/quizzes/{id}/result`; 429 detail key is `retake_available_at`, not `retry_at` as the B9 prompt says |
| B8 | Hardening, contract check green, deploy, keep-alive | todo | | Supabase JWT verification lands here |

## In-progress detail
- **Files touched, not finished:** `data/resources.yaml` (one replaced URL unverified; redirected URLs not yet updated)
- **What works right now:** `GET /health`, `GET /v1/roles`, `GET /v1/me` (demo profile, created on first call under `DEV_AUTH=1`); every error in the contract `Error` shape (404/405/422/500 + `ApiError`); CORS for `CORS_ORIGINS` and `chrome-extension://*`; tables created at startup.
- **Stubbed / fake (search `TODO(progress)`):**
  - `app/deps.py:get_auth_subject`: with `DEV_AUTH=0` every request gets 401 (no Supabase JWT verification yet) → B8.
- **Known failing tests / checks:** none. `check_contract.py` without `--only-implemented` exits 1 by design until all 29 operations are routed.

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
- Per-project quiz understanding will live in `profiles.project_understanding` (JSON keyed by repo/portfolio URL).

## Gotchas learned (one line each, append)
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
