# Handoff log — backend track (append only, newest at the bottom)

Templates and rules: `docs/HANDOFF.md`. Only the backend track writes here.


### [2026-10-07 14:28] claude-code — B1
Changed: `apps/api/` (FastAPI app factory, config, DB models, error handlers, DEV_AUTH dependency, routers `meta` + `profiles`, all contract schemas in `app/schemas/api.py`, `scripts/check_contract.py`, tests), `data/roles.yaml` (placeholder).
Works: `GET /health`, `GET /v1/roles`, `GET /v1/me` on the real backend (`cd apps/api && uv run fastapi dev app/main.py`, port 8000, `DEV_AUTH=1`). Errors on any route, including unknown ones, use the contract `Error` shape. CORS allows `CORS_ORIGINS` and `chrome-extension://*`.
Stubbed / mocked: `/v1/roles` serves one placeholder role until B2. Without `DEV_AUTH=1` every authenticated route returns 401 (JWT verification comes in B8). The other 26 operations are not routed yet; keep using the Prism mock for them.
Needs from other side: nothing.
Dependencies added (apps/api): fastapi[standard] (framework, uvicorn, test client), pydantic-settings (.env config), sqlalchemy (ORM), pyyaml (catalogues + contract check), psycopg[binary] (Supabase Postgres driver); dev: pytest, ruff.
Checks run: `uv run pytest -q` 16 passed; `uv run ruff check .` clean; `uv run python scripts/check_contract.py --only-implemented` 0 mismatches (3/29 routed); live `curl` of the three endpoints and a 404.

### [2026-10-07 15:49] claude-code — B2
Changed: `data/skills.yaml` (63 skills, aliases, detectors), `data/roles.yaml` (7 roles, importance, per-role weights), `data/resources.yaml` (130 resources, >= 2 per skill), `data/tutorial_names.txt`, `data/readme_templates.txt`, `apps/api/app/catalogue.py` (loaders, `normalize_skill`, `resources_for`, validation at startup), `apps/api/scripts/check_resource_urls.py`, tests.
Works: `GET /v1/roles` returns the real 7 roles (sde-backend, sde-frontend, full-stack, data-analyst, ml-engineer, devops-cloud, ui-ux-designer), 11-14 skills each. The server refuses to start if a catalogue file is inconsistent.
Stubbed / mocked: nothing in this task.
Needs from other side: nothing. Frontend: role ids and names are now final; skill ids in the contract examples all exist in the catalogue.
Notes for later backend tasks: skills with `detectors: {}` (system-design, excel, tableau, power-bi, most design skills) have no repository footprint by design; their evidence comes from experience bullets and portfolio items (SCORING §1), so B4/B5 must not treat an empty detector as an error. Role weights are internal (`RoleDef.weights`) and never serialised.
Checks run: `uv run pytest -q` 45 passed; `uv run ruff check .` clean; `check_contract.py --only-implemented` 0 mismatches; `scripts/check_resource_urls.py` 128 of 130 answered, 0 failed, 2 refused the script with 403 (w3.org WAI intro, tableau.com training) and were confirmed to exist with a separate fetch. No new dependencies.
