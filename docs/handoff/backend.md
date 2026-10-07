# Handoff log — backend track (append only, newest at the bottom)

Templates and rules: `docs/HANDOFF.md`. Only the backend track writes here.


### [2026-10-07 14:28] claude-code — B1
Changed: `apps/api/` (FastAPI app factory, config, DB models, error handlers, DEV_AUTH dependency, routers `meta` + `profiles`, all contract schemas in `app/schemas/api.py`, `scripts/check_contract.py`, tests), `data/roles.yaml` (placeholder).
Works: `GET /health`, `GET /v1/roles`, `GET /v1/me` on the real backend (`cd apps/api && uv run fastapi dev app/main.py`, port 8000, `DEV_AUTH=1`). Errors on any route, including unknown ones, use the contract `Error` shape. CORS allows `CORS_ORIGINS` and `chrome-extension://*`.
Stubbed / mocked: `/v1/roles` serves one placeholder role until B2. Without `DEV_AUTH=1` every authenticated route returns 401 (JWT verification comes in B8). The other 26 operations are not routed yet; keep using the Prism mock for them.
Needs from other side: nothing.
Dependencies added (apps/api): fastapi[standard] (framework, uvicorn, test client), pydantic-settings (.env config), sqlalchemy (ORM), pyyaml (catalogues + contract check), psycopg[binary] (Supabase Postgres driver); dev: pytest, ruff.
Checks run: `uv run pytest -q` 16 passed; `uv run ruff check .` clean; `uv run python scripts/check_contract.py --only-implemented` 0 mismatches (3/29 routed); live `curl` of the three endpoints and a 404.
