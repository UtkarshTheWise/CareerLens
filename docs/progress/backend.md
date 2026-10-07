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
- **Last updated:** 2026-10-07 23:59 IST by Claude Code (Sonnet 5.5)
- **Current task:** B7 done and verified (live job extraction + seeded cohort). Next: B9 (quiz), then B8.
- **State:** done   <!-- not started | in progress | blocked | done -->
- **Last green checks:** 2026-10-07 23:55 IST, from `apps/api`: `uv run pytest -q` (474 passed) · `uv run ruff check .` · `uv run python scripts/check_contract.py --only-implemented` (22/29 routed, 0 mismatches) · live `matchJob` with Gemini extraction

## Resume here (exact next step)
<!-- Precise enough for a model with zero context: file, function, what's left, the next command to run. -->
1. Start B9: paste its prompt from PROMPTS.md (plan with Opus, build with Sonnet: `/model opusplan`). New: `app/services/quiz_context.py`, `quiz.py`, `routers/quizzes.py`, `prompts/quiz_generate.md` + `quiz_grade.md`, quiz tables in `db/models.py`. Unrouted after B7: the 6 quiz operations (createQuiz, getQuiz, answerQuizQuestion, submitQuiz, getQuizResult, listQuizzes) and `tailorResume` (P2).
2. B9 contract with this code: `profiles.project_understanding` is a dict keyed by project URL (repo URL or portfolio URL) with values `{"understanding": "demonstrated|partial|not_demonstrated", "covered_skill_ids": [...], "quiz_id": "<uuid>"}`; `analysis_inputs.carry_understanding` reads it and a re-analysis keeps it. B9's submit re-scores via `ScoringInputs.model_validate(analysis.signals)` with updated projects, then rebuilds the stored report's `score`, `claims`, `gaps`, `projects` as `scripts/seed_demo.py:build_report` and `pipeline._run` do, and stores it with `pipeline.save_report(analysis, inputs, report)`.
3. B9 item 5 (seed gives ~60 % of students a verify result): set `ProjectInput.understanding` / `covered_skill_ids` on the generated inputs in `scripts/seed_demo.py:generate_inputs` before scoring. Seeded projects have no URLs, so key by `project_id` there. Cohort insights already read `ProjectAudit.understanding` of each student's top counted project, and `tests/test_seed.py` asserts the 12/18/10 bands, which a quiz bonus can shift: re-check it.
4. After any route or schema change: `cd apps/api && uv run python scripts/check_contract.py --only-implemented`. Seed locally with `cd apps/api && uv run python scripts/seed_demo.py` (uses `DATABASE_URL`).
5. Human: the GitHub token expires 2026-10-14; renew it in `careerlens-api/apps/api/.env`. Supabase needs the hotspot (college Wi-Fi blocks the DB ports).

## Task board
<!-- status: todo | doing | done | blocked · commit = short sha of the commit that finished it -->
| Id | Task | Status | Commit | Notes |
|---|---|---|---|---|
| B1 | Scaffold FastAPI, config, DB, errors, /health, /v1/roles, /v1/me, check_contract.py | done | 35c1be2 | all contract schemas already in `app/schemas/api.py` |
| B2 | Catalogues: skills.yaml, roles.yaml, resources.yaml + loaders/tests | done | e67462c | 63 skills, 7 roles, 130 resources; all links checked live |
| B3 | Ingest, PII stripping, LLM gateway, resume extraction | done | 1ced9ff | verified live 2026-10-07: Gemini fast and Groq both extract the fixture resume |
| B4 | GitHub collector, detectors, repo signals, rule flags | done | 024b6f8 | fixture: UtkarshTheWise (14 repos, 768 KB); `claim_mismatch` and `vague_description` flags are B6 |
| B5 | scoring.py + what-if + unit tests | done | c5b479d | 106 new tests; run on the recorded real profile and checked by hand |
| B6 | Pipeline, analyses endpoints, judging, roadmap planner, role-fit | done | 70d91bc | 5 endpoints incl. the milestone PATCH; live run verified; 102 new tests |
| B7 | Jobs match, applications, cohorts, seed_demo.py | done | e0dc64d | 9 ops routed (22/29); live extract_job check passed; 49 new tests |
| B9 | Project Understanding Check (quiz) | todo | | also `GET /v1/quizzes/{id}/result`; 429 detail key is `retake_available_at`, not `retry_at` as the B9 prompt says |
| B8 | Hardening, contract check green, deploy, keep-alive | todo | | Supabase JWT verification lands here |

## In-progress detail
- **Files touched, not finished:** none
- **What works right now:** `GET /health`, `GET /v1/roles` (7 real roles), `GET /v1/me` (demo profile, created on first call under `DEV_AUTH=1`), profile create/get/patch/delete, document upload (PDF/DOCX -> text); every error in the contract `Error` shape (404/405/422/500 + `ApiError`); CORS for `CORS_ORIGINS` and `chrome-extension://*`; tables created at startup. Services with no route yet: `github.collect()`, `detectors.analyse()`, `resume.extract_resume()`, `llm.generate_structured()`.
- **Stubbed / fake (search `TODO(progress)`):**
  - `app/deps.py:get_auth_subject`: with `DEV_AUTH=0` every request gets 401 (no Supabase JWT verification yet) → B8.
- **Known failing tests / checks:** none. `pytest -m live` passes (1 real call). Real server verified against Supabase on 2026-10-07 (create/upload/delete profile). `check_contract.py` without `--only-implemented` exits 1 by design until all 29 operations are routed.

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
- GitHub: public repos only (`privacy: PUBLIC`), top 8 non-forks by `pushedAt` get a file tree; **forks (up to 8) get commit facts but no tree**, so `unmodified_fork` is computable. Authored commits are matched by the GitHub account id, so commits made under an email not linked to the account don't count.
- Commit facts come from `history(first: 100)`: active span is measured on the newest 100 authored commits; `first_commit_share` is only computed for repos with <= 100 commits (else None, and the single_dump share rule can't fire).
- One GitHub fetch per repo serves manifests, content-regex files and import files; detector limits are constants at the top of `detectors.py` (>= 2 files per extension, 5 content files, 10 import files x 200 lines, 4 nested manifests).
- `default_readme` is a heuristic (starter marker in the first 500 chars, <= 4000 chars, none of the sections a student writes) because `readme_templates.txt` holds markers, not full starter text.
- An untouched fork gets `unmodified_fork` only, not also `single_dump` (one fact, one penalty). `.d.ts` files count as generated, not code.
- Flag severities are one fixed map (`FLAG_SEVERITY` in `detectors.py`); `RuleFlag` carries no id or estimated_gain, B6 adds `flag_id` and gain.
- Scoring is `scoring.score(ScoringInputs)`; inputs hold derived facts only (no raw resume/LinkedIn text), `today` is a parameter, so output is deterministic and re-scoring after a quiz needs no LLM or GitHub.
- `reasons[]` convention: `delta` = points (on the component's 0-100 scale) an item earned (+), or for an item that earned nothing the points it could have added (-). Positive deltas sum to the component score. A partially credited item has one + entry whose text names the shortfall, so + and - do NOT total 100.
- Coverage and claims use catalogue skills only; unknown listed skills ("Communication") are reported in `notes` as not scored. Required-but-unclaimed skills appear in `claims` with `claimed=false`.
- Untouched forks (0 own commits since forking) give no skill evidence; forks cap at `moderate`. Quiz effects use only artifact evidence when deciding "sole evidence" (a skills-list mention is not evidence).
- Confidence: others = GitHub + LinkedIn + readable portfolio item; >= 2 others (and GitHub, unless a design role) = high, 1+ = medium, else low (cap 60). Design roles with no portfolio score project quality 0 (penalised); engineering roles with no projects are "no data" (reweighted).
- Simulate: `ci` also adds a `ci-cd` hit to that project; a null `project_id` applies `add_signals` to every code project; resolving an `understanding_gap` flag assumes `demonstrated`; unknown ids raise `SimulationError`. Ids: project `proj-<slug>`, flag `flag-<slug>-<code-with-dashes>`, gap `gap-<skill_id>`.
- Free-text skill matching (`catalogue.find_skills_in_text`) skips a stoplist of ambiguous words ("next", "spring", "node", "caching" ...); it feeds only weak/moderate evidence.
- Pipeline (`services/pipeline.py`): own DB session per job, `status`+`progress` written per stage (10/25/40/55/70/85/92/100), failures of GitHub / one project review / a portfolio page / the planner degrade with a `notes` line instead of failing; only a missing resume or a failed resume extraction fails the job. Restart recovery fails stuck rows at startup.
- Reviews: max 6 per analysis, resume-matched repos first then by role relevance; untouched forks never reviewed; a repo not on the resume is judged on its tagline plus the first 600 chars of its README.
- Portfolio pages (`services/portfolio.py`) are fetched with SSRF protection (public addresses only, standard ports, hand-followed redirects re-checked, 1 MB, HTML only); residual DNS-rebinding risk is documented in the module.
- Roadmap (`services/planner.py`): the model picks ids and writes deliverables, Python validates ids, strips URLs, attaches catalogue resources, computes gains with `scoring.changes_gain`, orders by gain per hour, 4-7 milestones (top-up from a deterministic fallback), and always keeps an `understanding_gap` milestone.
- Matching (`services/matching.py`): skills resolve by alias, then by text scan ("Docker and Kubernetes"); unknown strings are not counted but named in `summary`; `scoring.skill_levels` gives levels for skills outside the analysed role. Cohort views re-score a student's stored signals when the requested role differs from the analysed one.
- Cohorts: plain Python over ORM rows (same on SQLite and Postgres); unverified rate needs >= 2 claimants; `understanding` is always returned (zeros and empty `by_skill` until quizzes exist); CSV cells starting with `= + - @` get a leading `'`.
- Seed: seeded RNG (2027) draws synthetic `ScoringInputs` until `scoring.score` lands in the wanted band, so 12/18/10 holds exactly; analyses are saved through `pipeline.save_report`; roadmaps come from the planner's no-LLM fallback; no usernames or URLs are invented.
- Recorded fixtures: `tests/fixtures/github/<login>/<fingerprint>.json` (status + body, never headers), replayed by `scripts/github_fixtures.py:ReplayTransport`; re-record with `uv run python scripts/record_github.py <login>` (needs token + a network that reaches api.github.com). Changing a GraphQL query changes its fingerprint, so re-record after editing `OVERVIEW_QUERY`, `commit_facts_query` or `files_query`.

## Gotchas learned (one line each, append)
- Pipeline tests drive the real code with `Env` in `tests/test_pipeline.py` (replayed GitHub fixture, `SchemaProvider` scripted LLM from `tests/llm_fakes.py`, stub page fetcher, `on_stage` recorder); the route gets its deps from `get_pipeline_deps`, which tests override. Starlette's TestClient finishes background tasks before returning, so a test can read the finished analysis right after the POST.
- The LLM gateway cache is shared across calls in one test (same prompt = cache hit), so tests that call a stage twice with different scripted replies must pass `refresh=True` or they get the first reply back.
- `strip_pii` treats a name-like first line as the person's name; READMEs and project descriptions must use `header_name=False` or "Campus API" becomes "[NAME]".
- The service is not multi-process safe for jobs: analyses run in the web process's thread pool; `recover_interrupted` fails any stuck row at startup.
- Live timings (hotspot, Gemini 3.5 flash + Groq fallback): cold run 65 s (GitHub ~25 s, six project reviews ~30 s, roadmap 4 s); a run with new prompts 125 s. Everything after is cached for 24 h.
- The backend reads `careerlens-api/apps/api/.env`. The main checkout `careerlens/apps/api/.env` is a different file; keys edited there do nothing until copied over (done once on 2026-10-07, old file kept as `.env.bak`).
- Live check 2026-10-07: `gemini-3.5-flash-lite` ok (~2 s), Groq `openai/gpt-oss-120b` ok (<1 s, strict schema works for ResumeProfile), `gemini-3.8-flash` returns 504 after the full timeout on a one-word prompt (3 tries); `gemini-3.7-flash` and `gemini-3.6-flash` answer in 3-4 s.
- Supabase from this laptop/network (checked 2026-10-07): the direct host `db.<ref>.supabase.co` does not resolve (IPv6-only); the session pooler host resolves but TCP 5432 and 6543 time out while 443 works, i.e. the network blocks database ports. Use SQLite locally.
- `make_engine` rewrites `postgresql://` / `postgres://` to `postgresql+psycopg://` (dashboard URLs would otherwise ask for psycopg2, which is not installed).
- Supabase tables are created by `create_all()` at startup and get `ENABLE ROW LEVEL SECURITY` (no policies) so the public anon key can't read them via PostgREST; the backend's `postgres` role bypasses RLS. New tables are covered automatically.
- Gemini benchmark 2026-10-07: during a demand spike both 3.7-flash and 3.6-flash returned 503 on most structured calls (3.7: 1 of 4 succeeded per round, 3.6: 0); 3.7 looked better then. Later `gemini-3.5-flash` succeeded 2 of 2 structured calls (~8 s each), so `.env` uses it for the smart tier. The gateway falls back to Groq on 503.
- `/health` reports the first configured provider, not a reachable one. Health should probe in B8.
- uvicorn does not show the app's INFO logs (no logging config yet): stage timings are invisible until B8 adds structured logging.
- PDF fixtures are hand-built ASCII; `tests/fixtures/.gitattributes` marks them binary so git doesn't rewrite line endings and break them.
- New fixtures: `uv run python tests/fixtures/make_fixtures.py`.
- `scripts/check_resource_urls.py` is live and manual; w3.org and tableau.com answer 403 to scripts (reported as `blocked`, not a failure).
- Skills with `detectors: {}` are intentional (no repo footprint); evidence for them comes from experience and portfolio items.
- When writing Python through the Bash tool, a double backslash (`\\b`) reaches Python as a single backslash, so `"\\b"` silently became a backspace character in a regex once. Use the Write/Edit tools for regex code, or build the characters with `chr(92)`.
- The GitHub token is a fine-grained PAT that expires 2026-10-14. Fixture tests never need it.
- `uv` lives in `~/.local/bin`; in Git Bash run `export PATH="$HOME/.local/bin:$PATH"` first if `uv` isn't found.
- Tests set `DATABASE_URL=sqlite:///:memory:` and `DEV_AUTH=1` in `tests/conftest.py` before importing the app, so they never read the real `.env` database.
- `Settings.cors_origins` is a comma-separated string (a `list[str]` field would make pydantic-settings expect JSON in `.env`); use `settings.cors_origin_list`.
- Starlette prints a deprecation warning about `httpx` in `TestClient`; harmless.

- Tests import the seed as `scripts.seed_demo` (the rootdir is on the path); the script itself only imports from `app`.
- Bash tool heredocs with apostrophes sometimes fail with "unexpected EOF"; write files with the Write/Edit tools instead.

## Blocked on / open questions
- none

## Environment
- `apps/api/.env` keys set: GEMINI ☐ GROQ ☐ GITHUB_TOKEN ☐ DATABASE_URL ☐ (never paste values here; not checked by the agent, the file is deny-listed)
- Run: `cd apps/api && uv sync && uv run fastapi dev app/main.py` → :8000
- Tooling on this machine: uv 0.12.23 (installed 2026-10-07), Python 3.12.15 via uv (`apps/api/.python-version`), Node 22.16.0, pnpm 10.12.3
- Gemini model IDs confirmed in AI Studio: —
- `apps/api/.env.example` lists every key; it defaults `DATABASE_URL` to `sqlite:///./dev.db`
- Contract frozen at v0.2.0; lint with `npx @redocly/cli lint contracts/openapi.yaml` (config in `redocly.yaml`). Freeze changes are listed in `docs/handoff/integration.md`.
