# CareerLens API

FastAPI backend for CareerLens: it reads a student's resume, GitHub and portfolio, scores job readiness with
explainable evidence, and serves the placement-cell cohort view. The HTTP shapes are defined by
[`contracts/openapi.yaml`](../../contracts/openapi.yaml); this service matches it exactly (checked in CI-style by
`scripts/check_contract.py`). Product rules and scoring live in [`docs/`](../../docs) (`SCORING.md`,
`PIPELINE.md`, `QUIZ.md`).

## Run it locally

```bash
cd apps/api
uv sync
cp .env.example .env          # then fill in keys; DEV_AUTH=1 is already set for local work
uv run fastapi dev app/main.py   # http://localhost:8000/docs
```

With `DEV_AUTH=1` every request is the demo student and counts as placement staff. Create the demo cohort
(40 synthetic students, no network, no LLM) with:

```bash
uv run python scripts/seed_demo.py          # idempotent: replaces only its own cohort
```

`uv` lives in `~/.local/bin` on this machine; in Git Bash run `export PATH="$HOME/.local/bin:$PATH"` first.

## Checks

```bash
uv run pytest -q                          # offline: recorded GitHub, scripted LLM replies, fake clock
uv run ruff check .
uv run python scripts/check_contract.py   # every contract operation routed, no drift (29/29)
uv run pytest -m live -q                  # optional: one real LLM call (needs keys and quota)
```

Tests never touch the network. Anything that does is marked `@pytest.mark.live` and skipped by default.

## Configuration

Read from `apps/api/.env` and the environment (see [`.env.example`](.env.example)). Never commit `.env`.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `sqlite:///./dev.db` locally; a Supabase `postgresql://...` string in deploy (the app switches the driver). |
| `GEMINI_API_KEY`, `GEMINI_MODEL_FAST`, `GEMINI_MODEL_SMART` | Primary LLM. Smart tier writes quizzes and grades answers, fast tier does the rest. |
| `GROQ_API_KEY`, `GROQ_MODEL` | Fallback LLM when Gemini is rate-limited or down. |
| `OLLAMA_URL`, `OLLAMA_MODEL` | Optional last-resort local model. |
| `GITHUB_TOKEN` | Fine-grained token, public repositories read-only. Needed for real analyses and quizzes. |
| `DEV_AUTH` | `1` accepts every request as the demo student (and as staff). Local only. |
| `ENVIRONMENT` | `production` refuses `DEV_AUTH=1` and refuses to start without a way to verify tokens. |
| `SUPABASE_JWT_SECRET` | Projects that sign tokens with a shared secret (HS256). |
| `SUPABASE_URL` | Projects with asymmetric signing keys: tokens are checked against `<url>/auth/v1/.well-known/jwks.json`; also pins the issuer. |
| `PLACEMENT_STAFF` | Comma-separated emails or Supabase user ids that may read cohort data. A token with `app_metadata.role = "placement"` also counts. |
| `CORS_ORIGINS` | Comma-separated web origins. Chrome extension origins are allowed by pattern in code. |
| `QUIZ_COOLDOWN_MINUTES` | Wait between verify quizzes on one project (default 60; 24 h in production). |
| `LOG_LEVEL`, `LOG_FORMAT` | `INFO` / `json` (one JSON object per line); `text` for a readable local format. |
| `MAX_BODY_KB`, `MAX_UPLOAD_KB` | Request body limits: 1024 for JSON, 6144 for document uploads (a 5 MB file plus overhead). |
| `DB_STATEMENT_TIMEOUT_MS` | Optional Postgres statement timeout (0 = off). Some poolers reject the startup option it uses; if the app cannot connect after enabling it, set it back to 0. |

## Authentication and access

* Students sign in with Supabase; the web app sends `Authorization: Bearer <access token>`. The token is
  verified here (signature, expiry, audience `authenticated`, issuer when `SUPABASE_URL` is set). Failures are a
  generic `401`.
* Every student route is scoped to the token's user: someone else's profile, analysis, quiz or application is a
  `404`.
* Cohort routes (`/v1/cohorts/...`) need placement staff (`403` otherwise).
* The first sign-in has no profile yet: `GET /v1/me` is `404` until the app calls `POST /v1/profiles`.

## Bring your own AI key

A student can use their own Gemini or Groq key so the shared free quota is not spent. The web app (Settings) keeps
the key in the browser and sends `X-LLM-Provider` (`gemini` or `groq`) and `X-LLM-Key` on the requests that call a
model: startAnalysis, createQuiz, getQuiz, answerQuizQuestion, submitQuiz, getQuizResult, matchJob, tailorResume.
When present, only that key is used (no fallback to the shared keys), the per-user hourly limits are skipped, and it is
held in memory for the request (an analysis keeps it for its background job). It is never stored, cached or logged. A
malformed pair is `422 invalid_llm_key`; a key the provider rejects is `400 invalid_llm_key` (a failed analysis shows
the same message). These headers are deliberately not in `contracts/openapi.yaml` and are hidden from the schema.
See `app/services/byok.py`.

## What is logged

One JSON line per request (id, method, route template, status, milliseconds) plus stage timings and LLM/GitHub
call summaries. Never resume text, request bodies, query strings, headers or tokens. Library loggers that would
print file contents or URLs (`pdfminer`, `httpx`, ...) are pinned to WARNING.

## Recording GitHub fixtures

Tests replay recorded GitHub responses from `tests/fixtures/github/<login>/`. To record a new profile (needs a
token and a network that reaches `api.github.com`):

```bash
uv run python scripts/record_github.py <login>
```

Changing a GraphQL query in `app/services/github.py` changes its fingerprint, so re-record afterwards. Other
fixtures: `uv run python tests/fixtures/make_fixtures.py`.

## Deploying

`render.yaml` at the repository root describes one free Render web service (`rootDir: apps/api`).

1. Create the service from the blueprint on a **personal** GitHub repository, then fill the `sync: false`
   variables in the Render dashboard: `DATABASE_URL`, `SUPABASE_JWT_SECRET` or `SUPABASE_URL`,
   `PLACEMENT_STAFF`, `CORS_ORIGINS`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `GITHUB_TOKEN`.
2. Tables are created at startup (`create_all`), with row-level security switched on so the public Supabase key
   cannot read them.
3. `GET /health` returns `200` only if the database answers; Render uses it as its health check.
4. Add the repository secret `API_URL` (for example `https://careerlens-api.onrender.com`). The workflow
   `.github/workflows/keepalive.yml` pings `/health` daily, which wakes Render and runs a query on Supabase so
   neither sleeps or pauses. Call `/health` yourself a minute before a demo: a cold start takes about a minute.

### Gotchas

* **Supabase from a campus network:** the direct host `db.<ref>.supabase.co` is IPv6-only and the pooler's
  database ports (5432, 6543) are often blocked on college Wi-Fi. Use SQLite locally, or a phone hotspot.
* Use the session-pooler connection string; the app disables prepared statements so a transaction pooler also works.
* The service runs analyses in background tasks inside the web process, so run **one** instance. A restart marks
  any analysis that was running as failed and the student starts it again.
* Free-tier LLM quotas are small: quiz creation costs one smart-tier call (two if a replacement round is needed),
  submitting costs one more. Pre-generate demo quizzes before judging; everything is cached for 24 hours.

## Layout

```
app/main.py            app factory, middleware, routers, startup checks
app/config.py          settings (pydantic-settings) and the production guard
app/deps.py            database session, auth context, ownership checks
app/routers/           one file per contract tag
app/schemas/api.py     Pydantic models mirroring the contract exactly
app/schemas/llm.py     small LLM response schemas
app/services/          pipeline, scoring (pure), detectors, github, llm gateway, quiz, matching, cohorts, tailor
app/prompts/           prompt templates (## System / ## User)
scripts/               check_contract, seed_demo, record_github, check_resource_urls
tests/                 offline tests and fixtures
```
