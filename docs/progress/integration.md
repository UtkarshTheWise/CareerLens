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
- **Current task:** I7 IN PROGRESS: (a) homepage style across the app, (b) in-app resume builder (plain-text upload), (c) cohort skill filters. Plan file: ~/.claude/plans/wild-nibbling-feather.md (summary in docs/handoff/integration.md). integration was fast-forwarded to origin/frontend/codex (f506ed2) first.
- **State:** in progress   <!-- not started | in progress | blocked | done -->
- **Last green checks:** 2026-10-08, integration worktree (Node 22.16.0, pnpm 10.12.3): backend 683 tests / ruff / `check_contract.py` 29/29 · `apps/api/scripts/smoke_e2e.py` 499 checks (dev + token mode) · web lint, typecheck, build (also configured), native tests incl. ai-key · extension typecheck, build, 24 tests

## Resume here (exact next step)
<!-- Precise enough for a model with zero context: file, function, what's left, the next command to run. -->
1. Ask the human to follow `docs/AUTH_SETUP.md` (Google Cloud + Supabase), then give you: Supabase URL, anon key, token type (HS256 secret or signing keys), staff emails, deployed web URL. Put them in `apps/web/.env.local`, `apps/extension/.env.local` (rebuild) and the API env (Render). Then the human runs the manual checks in `docs/AUTH_SETUP.md` section 5 and `docs/DEMO_CHECKLIST.md`.
2. With the human's OK: `cd` to the backend worktree or the integration worktree and fast-forward `main` (`git push origin integration:main` after `git fetch` shows `origin/main` is an ancestor). Update `docs/progress/backend.md` / `frontend.md` only to say integration is done (do not rewrite their history).
3. Open decisions from the review are listed in `docs/handoff/integration.md` (cohort membership for real students is the important one).
4. Re-run after any change: `cd apps/api && uv run python scripts/smoke_e2e.py` (both modes) and the web/extension checks above.
5. Work in `D:/Programming/DataQuest/CareerLens/careerlens-integration`; the shell resets to the backend worktree on every call, so `cd` first.

## Task board
<!-- status: todo | doing | done | blocked · commit = short sha of the commit that finished it -->
| Id | Task | Status | Commit | Notes |
|---|---|---|---|---|
| P0 | Contract freeze v0.2.0, root workspace, api-client, .env.example | done | see `git log --grep freeze` | awaiting human tag `v0.2.0` |
| I1 | Integration plan (plan mode) | done | | approved plan includes Google sign-in |
| I2 | Merge, regenerate client, drift fixes, builds green | done | see git log | clean merge; client unchanged; sign-in added for web + extension |
| I3 | End-to-end smoke script + demo checklist | done | see git log | green in dev and token mode; found and fixed 3 backend drifts |
| I4 | Independent review + fixes | done | see git log | 6 fixes + 7 open decisions in docs/handoff/integration.md |
| I6 | Animated landing page at `/` (Get started -> /login) | done | see git log | `/` is now a bare route in app-shell; respects reduced motion |
| I5 | `/extension` install page + zip, Settings "your own AI key" (BYOK headers), prod push | done | see git log | extension itself has no key field yet (follow-up) |

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
