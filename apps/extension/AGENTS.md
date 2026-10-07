# apps/extension — Chrome extension rules (owner: Codex)

Stack: Manifest V3, Vite + React + TypeScript, Tailwind with the same tokens as `docs/DESIGN.md`, types from `packages/api-client`.

## Behaviour

- **Side panel** (`chrome.sidePanel`), opened by the toolbar action (needs a user gesture). No auto-injected overlays on job sites.
- Extraction order, only when the user clicks "Analyse this job":
  1. `script[type="application/ld+json"]` → find `@type: JobPosting` (also inside `@graph`) → title, hiringOrganization.name, jobLocation, description (strip HTML), validThrough. `source: "jsonld"`.
  2. Site adapters (selectors in `src/adapters/*.ts`, one file per site: linkedin, greenhouse, lever, workday, naukri, generic). `source: "dom"`.
  3. Fallback: send visible main text (≤ 20k chars) as `description` with `source: "llm"`; the backend extracts.
- Read only the active tab, only on click (`activeTab` + `scripting` permissions; avoid broad host permissions). Never read LinkedIn profile pages.
- Call `POST /v1/jobs/match`; show two rings: **Keyword match** and **Evidence-backed match**, then matched (with level pills), missing, unverified lists.
- "Save to tracker" → `POST /v1/applications` with both match numbers.
- Options page: API base URL (default `http://localhost:8000`), profile id (prefilled from `GET /v1/me`), theme.
- Store settings in `chrome.storage.local`. Never store LLM keys. Send `Authorization: Bearer dev` in development.

## Checks

`pnpm --filter extension typecheck && pnpm --filter extension build`, then load `dist/` unpacked and test on one Greenhouse, one Lever and one LinkedIn job page.
