# Progress — Integration track

<!--
Living snapshot for context hand-off. ANY agent/model continuing this track reads this first.
Overwrite sections to reflect the truth NOW; don't append history (history and messages go in docs/handoff/integration.md).
Update after every meaningful step, not just at the end: usage limits cut sessions off without warning.
Keep under ~150 lines. Commit it together with the code it describes.
-->

## Status
- **Track:** integration · **Owns:** wiring + drift fixes across the repo (Phase 3 only)
- **Branch / worktree:** `integration` · worktree `../careerlens-integration` (no deny rules; the backend worktree denies apps/web and apps/extension)
- **Last updated:** 2026-10-08 Claude Code (Sonnet 5.5)
- **Current task:** I2 in progress. Merged `origin/frontend/codex` into `main` (B1-B9 + B8) cleanly (no overlapping files). Baseline green. End-to-end smoke written and green in both auth modes (242 + 257 checks), 3 backend drifts fixed. Web and extension Google sign-in done and documented (`docs/AUTH_SETUP.md`); 27 web + 24 extension tests, both build in configured and unconfigured modes. Next: independent review (I4), then ask the human to do the `docs/AUTH_SETUP.md` section 5 manual checks, then fast-forward `main`.
- **State:** in progress   <!-- not started | in progress | blocked | done -->
- **Last green checks:** 2026-10-08, from the integration worktree (Node 22.16.0, pnpm 10.12.3): `pnpm install --frozen-lockfile` · `pnpm gen:client` (no content diff) · web `lint`, `typecheck`, `build`, 22 native tests · extension `build` and 20 tests · backend 653 tests / ruff / `check_contract.py` (29/29) on the same commit

## Resume here (exact next step)
<!-- Precise enough for a model with zero context: file, function, what's left, the next command to run. -->
1. Approved plan: `~/.claude/plans/refactored-giggling-bachman.md` (Phase 3 with real Google sign-in via Supabase). Order now: (a) DONE `apps/api/scripts/smoke_e2e.py` (+ `tests/e2e_server.py` harness) and `docs/DEMO_CHECKLIST.md` (I3); run `cd apps/api && uv run python scripts/smoke_e2e.py` (both modes), (b) DONE web sign-in (`lib/auth/{supabase,session,user}.ts`, `components/auth/*`, `app/login`, `app/auth/callback`, token middleware `authMiddleware` in `lib/api/client.ts`, gate + sign-out in `app-shell.tsx`, name prefill in onboarding; on only when `NEXT_PUBLIC_SUPABASE_URL` and `_ANON_KEY` are set, see `apps/web/.env.example`), (c) DONE extension sign-in (`src/auth.ts` Supabase client over `chrome.storage.local`, `chrome.identity.launchWebAuthFlow` + PKCE, `src/auth-helpers.ts` tested, `api.ts` token per request, Options "Account" card, manifest `identity` + `key`; extension id `bchilaidlnimfdagenlcpoannjomfkil`; on only when `VITE_SUPABASE_URL`/`_ANON_KEY` are set), (d) DONE `docs/AUTH_SETUP.md`, (e) independent review (I4), (f) fast-forward `main` to `integration` with the user's OK.
2. Work in `D:/Programming/DataQuest/CareerLens/careerlens-integration` (branch `integration`). The shell resets to the backend worktree each call: always `cd` to the integration worktree first.
3. Needed from the human for sign-in: Supabase URL + anon key, token type (HS256 secret or signing keys), Google provider enabled in Supabase, staff emails, deployed web URL. Until then the apps keep dev mode (`Bearer dev`).
4. Machine quirk: `D:\postcss.config.mjs` exists at the drive root and Vite picks it up when building anything under `D:\`; the extension's Vite configs now pin an inline empty PostCSS config. Do not delete the stray file (not ours).

## Task board
<!-- status: todo | doing | done | blocked · commit = short sha of the commit that finished it -->
| Id | Task | Status | Commit | Notes |
|---|---|---|---|---|
| P0 | Contract freeze v0.2.0, root workspace, api-client, .env.example | done | see `git log --grep freeze` | awaiting human tag `v0.2.0` |
| I1 | Integration plan (plan mode) | done | | approved plan includes Google sign-in |
| I2 | Merge, regenerate client, drift fixes, builds green | doing | | merge + baseline done; sign-in work pending |
| I3 | End-to-end smoke script + demo checklist | done | see git log | green in dev and token mode; found and fixed 3 backend drifts |
| I4 | Independent review + fixes | todo | | |

## In-progress detail
- **Files touched, not finished:** —
- **What works right now:** —
- **Stubbed / fake (search `TODO(progress)`):** —
- **Known failing tests / checks:** —

## Decisions made (one line each, append)
- 2026-10-08 Sign-in is Supabase + Google (user's choice). Apps stay in dev mode when the Supabase env values are empty. Extension id is fixed by a committed public `key`; the private key was discarded on purpose.
- 2026-10-08 Drifts found by the smoke test and fixed in the BACKEND (contract unchanged): `/health` sent `llm_provider: null` (contract: string, now omitted); practice `QuizResult` sent `focus_lost_total: null` (now omitted); under DEV_AUTH `/v1/me` ignored a freshly created profile (the newest profile now becomes the dev user's).
- 2026-10-07 Contract frozen at v0.2.0. Later changes only via CCR (docs/HANDOFF.md).
- Freeze added: `GET /v1/quizzes/{quiz_id}/result`, `PATCH /v1/analyses/{analysis_id}/roadmap/{milestone_id}`, `default` Error response on every operation, `QuizStatus` schema.
- Freeze changed: `ProjectAudit.repo_url` → `url` (+ `demo_url`, `counted_in_score`, `design_subscores`, `signals`, `issues`); `SkillGap.claimed` (required); `AnalysisStatus.progress` required; `AnalysisSummary.verified_skills`; `QuizQuestion.time_remaining_s`; `QuizAnswerFeedback.choice_id`/`text`; `CohortStudent.github_username`/`analysis_id`; removed `more_commits` from `add_signals`; 429 detail key is `retake_available_at`.
- `ProjectFlag.severity` has no rule in SCORING.md: backend uses a fixed per-code map.
- `RoleFit.score` has no formula in SCORING.md: it is the JRS recomputed for each catalogue role; report keeps the top 3.
- Bare skill strings (`JobMatch.missing`/`unverified`, `RoleFit.top_missing`, `CohortStudent.top_gap`) are display names, not ids.
- Skill ids used in contract examples (python, fastapi, sql, docker, pytest, react, kubernetes, aws, redis, ci-cd, javascript, system-design) should exist in `data/skills.yaml` so mock and real data line up.
- Spec lint config is `redocly.yaml` (structural rules + example validation; style rules off).

## Gotchas learned (one line each, append)
- Prism `-d` (dynamic) ignores the contract examples, returns lorem-ipsum data and randomly answers 500 on `/v1/analyses/{id}` (json-schema-faker crash, also on the pre-freeze spec). Run the mock WITHOUT `-d` to get the persona data.
- In flow-style YAML (`{ ... }`) an unquoted description containing a comma silently becomes extra keys. Quote such descriptions; the lint catches it (`struct`).
- The contract examples share data through YAML anchors (`&ex_score`, `&ex_claim`, `&ex_project`, `&ex_milestone`) defined inside the `AnalysisReport` example.

## Blocked on / open questions
- 

## Environment
- Backend :8000, web :3000, extension loaded from `apps/extension/dist`
- This machine: Node 22.16.0, pnpm 10.12.3, Python 3.11.4; `uv` is NOT installed yet (needed before B1; it can fetch Python 3.12)
- Merged commits: backend/claude @ — · frontend/codex @ —
