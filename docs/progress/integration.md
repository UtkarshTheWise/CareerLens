# Progress — Integration track

<!--
Living snapshot for context hand-off. ANY agent/model continuing this track reads this first.
Overwrite sections to reflect the truth NOW; don't append history (history and messages go in docs/handoff/integration.md).
Update after every meaningful step, not just at the end: usage limits cut sessions off without warning.
Keep under ~150 lines. Commit it together with the code it describes.
-->

## Status
- **Track:** integration · **Owns:** wiring + drift fixes across the repo (Phase 3 only)
- **Branch / worktree:** `integration` · main checkout `careerlens/`
- **Last updated:** 2026-10-07 13:57 IST by Claude Code (Opus 5.5)
- **Current task:** Phase 0 contract freeze: done. Phase 3 (I1) not started.
- **State:** not started   <!-- not started | in progress | blocked | done -->
- **Last green checks:** 2026-10-07 `npx @redocly/cli lint contracts/openapi.yaml` valid · `pnpm gen:client` · `tsc --noEmit -p packages/api-client` · Prism static mock serves `/v1/roles` (200 with bearer, 401 without)

## Resume here (exact next step)
<!-- Precise enough for a model with zero context: file, function, what's left, the next command to run. -->
1. Start I1: run its prompt from PROMPTS.md.

## Task board
<!-- status: todo | doing | done | blocked · commit = short sha of the commit that finished it -->
| Id | Task | Status | Commit | Notes |
|---|---|---|---|---|
| P0 | Contract freeze v0.2.0, root workspace, api-client, .env.example | done | see `git log --grep freeze` | awaiting human tag `v0.2.0` |
| I1 | Integration plan (plan mode) | todo | | |
| I2 | Merge, regenerate client, drift fixes, builds green | todo | | |
| I3 | End-to-end smoke script + demo checklist | todo | | |
| I4 | Independent review + fixes | todo | | |

## In-progress detail
- **Files touched, not finished:** —
- **What works right now:** —
- **Stubbed / fake (search `TODO(progress)`):** —
- **Known failing tests / checks:** —

## Decisions made (one line each, append)
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
