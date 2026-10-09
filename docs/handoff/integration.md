# Handoff log — integration track (append only, newest at the bottom)

Templates and rules: `docs/HANDOFF.md`. Only the integration track writes here.

### [setup] human — Phase 0
Contract v0.1.0 drafted.

### [setup] human — contract v0.2.0
Added Project Understanding Check (docs/QUIZ.md): quiz endpoints and schemas, `understanding_gap` flag, `set_understanding` in simulate, cohort understanding stats. Removed interview-questions endpoint. Awaiting freeze.

### [2026-10-07 13:57] claude-code — P0 contract freeze v0.2.0
Changed: `contracts/openapi.yaml` (review changes + examples), root `package.json` / `pnpm-workspace.yaml` / `pnpm-lock.yaml`, `packages/api-client/` (wrapper + generated `schema.d.ts`), `apps/api/.env.example`, `redocly.yaml`.
Contract changes since the draft:
- New: `GET /v1/quizzes/{quiz_id}/result` (re-fetch a submitted or auto-submitted quiz result), `PATCH /v1/analyses/{analysis_id}/roadmap/{milestone_id}` (`{done}`), `QuizStatus` schema, `default` Error response on every operation.
- Renamed: `ProjectAudit.repo_url` → `url` (repo URL for code, portfolio page URL for design).
- Added fields: `ProjectAudit.demo_url`, `counted_in_score` (required), `design_subscores`, `signals`, `issues`; `SkillGap.claimed` (required); `AnalysisSummary.verified_skills`; `QuizQuestion.time_remaining_s`; `QuizAnswerFeedback.choice_id`, `text`; `CohortStudent.github_username`, `analysis_id`.
- Tightened: `AnalysisStatus.progress` is required. Removed `more_commits` from `SimulationRequest…add_signals`. createQuiz 429 detail key is `details.retake_available_at`.
- Fixed: five flow-style descriptions containing commas were parsing as extra schema keys; now quoted.
Works: static Prism mock returns one consistent synthetic persona (CSE student, sde-backend, JRS 65.1) for analyses, roles, me, cohort insights/students and job match.
Stubbed / mocked: everything; no backend code yet.
Needs from other side:
- Codex: root package files are yours from here. Run the mock without `-d`. Add `transpilePackages: ["@careerlens/api-client"]` to the Next config. Use `time_remaining_s` for the verify countdown, not the client clock. `ApplicationCreate.company` is required but `JobPosting.company` can be null: fall back to the page hostname when saving from the extension.
- Backend: implement the two new endpoints (B6 roadmap PATCH, B9 quiz result). Keep the example skill ids in `data/skills.yaml`. Install `uv` on this machine before B1.
- Human: AGENTS.md and RUNBOOK.md still show the mock command with `-d`; drop the flag there. Tag `v0.2.0`.
Checks run: `npx @redocly/cli lint contracts/openapi.yaml` valid (examples validated against their schemas); `pnpm gen:client` ok; `pnpm exec tsc --noEmit -p packages/api-client` ok; Prism `-d` starts and serves `/v1/roles` 200 with `Authorization: Bearer dev`, 401 without; static mode same plus persona data. `check_contract.py` not run (does not exist until B1).

### [2026-10-08] claude-code — Phase 3 integration (I1-I4)
**State.** Branch `integration` = `main` (B1-B9, B8) + `frontend/codex` (F1-F9) + the work below. Codex had finished F8 (extension) before going quiet, so nothing was taken over. All suites green on the same commit: backend 666 tests, ruff, `check_contract.py` 29/29 (no flags); web lint, typecheck, build (also with sign-in configured), 27 native tests; extension typecheck, build, 24 tests; `apps/api/scripts/smoke_e2e.py` 499 checks over real HTTP (dev mode and token mode).
**Merge.** `origin/frontend/codex` merged with no conflicts (no overlapping files; contract unchanged, `pnpm gen:client` gives no content diff). Worktree note: the backend worktree denies edits to `apps/web`, `apps/extension`, `packages/api-client`, so integration runs in `../careerlens-integration`. Machine quirk: a stray `D:\postcss.config.mjs` made the extension build fail; the extension's Vite configs now pin an inline empty PostCSS config.
**Drift found by the smoke test and fixed in the backend (contract untouched):** `/health` sent `llm_provider: null` (now omitted); practice `QuizResult` sent `focus_lost_total: null` (now omitted); under `DEV_AUTH`, `/v1/me` ignored a profile just created (the newest profile now becomes the dev user's).
**New: Google sign-in via Supabase.** Web (`lib/auth`, `components/auth`, `/login`, `/auth/callback`, token middleware in `lib/api/client.ts`, gate and sign-out in the shell, name prefill) and extension (`src/auth.ts` with PKCE through `chrome.identity.launchWebAuthFlow`, session in `chrome.storage.local`, Options "Account" card, manifest `identity` permission and a fixed public `key`, extension id `bchilaidlnimfdagenlcpoannjomfkil`). Both stay in dev mode when the Supabase env values are empty. Setup steps for Google Cloud and Supabase: `docs/AUTH_SETUP.md`. Dependencies added: `@supabase/supabase-js` (web, extension), `jsonschema` (api dev only, for the smoke test's contract validation).
**Independent review (fresh subagent, I4): fixed.**
- Portfolio: a malformed link (`http://exa..mple.com`) raised `UnicodeError` and failed the whole analysis (and a design-project quiz); now an unsafe URL, the page counts as unreadable.
- PII reached the LLM from the quiz: generation prompts (description, README, repository code) and grading prompts (question context, the student's answer) are now passed through `strip_pii` and restored afterwards; line numbers are unaffected.
- Grader prompt injection: the student's answer is fenced in `<student_answer>` tags (a literal closing tag is removed) and the system prompt says the contents are data, never instructions.
- A practice answer could be saved ungraded when the grader failed after a partial reply, so a resend returned `already_answered`; the answer is now attached only after grading succeeds.
- A verify quiz opened but never answered no longer becomes `not_demonstrated` after its time budget; it is closed as abandoned with no effect (partial attempts are still scored with zeros for the rest, per QUIZ.md 1.6).
- Per-user rate limits (in memory, last hour; DEV_AUTH exempt; `RATE_LIMIT_*_PER_HOUR`, 0 = off) on `startAnalysis` (12), `createQuiz` (30), `tailorResume` (30), `matchJob` (120): `429 rate_limited` with `details.retry_after_s`.
- DB errors no longer put bound values (resume or answer text) in logs (`hide_parameters`); NUL characters stripped from extracted text (Postgres rejects them); PDF uploads over 25 pages and DOCX files that unpack to over 50 MB are refused with 422.
- UI: the understanding badge for `not_demonstrated` now reads "Not demonstrated yet" in a warning tone (was "Review needed" in red).
**Reviewer findings NOT fixed (decisions for the humans):**
1. **No way to put real students in a cohort.** There is no cohort-creation endpoint, `listCohorts` is staff-only, and onboarding has no cohort field, so only seeded students appear in the placement view. Needs a contract change (for example staff-created cohorts with a join code and a `cohort_id` choice in onboarding/settings) or a staff-side import. For the demo the seeded cohort is enough.
2. `github_username` is self-declared and not verified to belong to the student; evidence from another person's account would be credited. The verify quiz is the mitigation. A fix would be GitHub OAuth sign-in or a verification gist.
3. A verify quiz taken on an older analysis updates `profile.project_understanding` and that analysis but not a newer analysis until the next re-scan.
4. Two parallel `createQuiz` calls for one project can both pass the one-open-quiz check (the LLM call between check and insert is slow). Low impact.
5. `deleteProfile` cannot remove LLM cache rows derived from the resume (they are keyed by content hash).
6. A student can set `cohort_id` on their own profile if they know a cohort UUID (UUIDs are only listed to staff).
7. DNS rebinding window in the portfolio fetcher (documented in `portfolio.py`).
**Not verified (needs your Supabase/Google project, a browser or a deploy):** the Google consent screen and token verification against a real project (HS256 and JWKS are tested with locally signed tokens), the extension's sign-in window, browser rendering and accessibility of the new pages, the Render deploy and the keep-alive workflow, `tailorResume` and a good-answers verify quiz with real models, a current LinkedIn job page. Checklists: `docs/AUTH_SETUP.md` section 5 and `docs/DEMO_CHECKLIST.md`.

### [2026-10-08] claude-code - I5: install page and bring-your-own AI key
**What.** `/extension` (steps, troubleshooting, zip download from `apps/web/public/downloads/`, nav entry), Settings page (account + "Your own AI key (optional)"), `scripts/pack_extension.py` / `pnpm pack:extension`.
**Non-contract headers (decision, no Contract Change Request).** `X-LLM-Provider` + `X-LLM-Key`, optional, sent by the web client only on model-calling operations, hidden from OpenAPI. The key lives in browser localStorage; the API uses only that provider for the request, never stores/caches/logs it, skips the hourly limits. Bad pair -> 422 `invalid_llm_key`; rejected key -> 400 `invalid_llm_key`. Stays out of `contracts/openapi.yaml` on purpose; if the humans want it documented there, that is a contract change (regenerates the client).
**Not done / follow-ups.** The extension has no key field (its model use is rare: reading a page with no listed skills). The zip must be repacked when the extension changes. Quota is still shared for users without a key; consider Gemini billing, fewer calls per analysis, or cached demo flows.
**Not verified.** A real Gemini/Groq call with a user key, the signed-in Settings UI in a browser, loading the zip into Chrome.

### CCR-1 [2026-10-09] by claude-code (integration)
Status: APPROVED (owner, explicit request in session 2026-10-09: "let users make their first resume on the platform")
Endpoint/schema: `POST /v1/profiles/{profile_id}/documents` (`uploadDocument`)
Change: description and `file` description only; no shape change. The endpoint also accepts a UTF-8 plain-text resume in a file named `*.txt`.
Why: students without a resume build one in the app; the web sends the generated text as `resume.txt` through the same endpoint.
Impact: backend accepts `.txt` (strict UTF-8, no control characters, 5 MB / 60k chars); web adds a resume builder; extension none.

### CCR-2 [2026-10-09] by claude-code (integration)
Status: APPROVED (owner, same session: "filters for searching students on the placement cohort view")
Endpoint/schema: `GET /v1/cohorts/{cohort_id}/students` (`listCohortStudents`), `GET /v1/cohorts/{cohort_id}/export` (`exportCohort`), `#/components/schemas/CohortStudent`, new `#/components/schemas/MatchedSkill`
Change: new optional query params `skill` (repeatable, max 10), `skill_match` (all|any), `min_level` (strong|moderate|weak|unverified, default moderate), `min_score`, `band` (repeatable), `sort` (score_asc default|score_desc|coverage_desc|name), `limit`; export also gets `at_risk_only`. `CohortStudent.matched_skills` (optional array of `MatchedSkill`), empty without a skill filter.
Why: a company asks for e.g. "2 students with a good score who have skill X"; all defaults keep today's behaviour.
Impact: backend filters in `services/cohorts.py`; web placement screen gets a "Find students" section; extension none (client regenerated, no code change).
