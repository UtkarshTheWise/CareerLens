# Progress — Frontend track

## Status
- **Track:** frontend; owns apps/web/apps/extension and frontend workspace files.
- **Branch / worktree:** frontend/codex; C:/Users/User/Desktop/CareerLens/careerlens-web
- **Last updated:** 2026-10-07 22:45 Asia/Dubai by Codex (GPT-6).
- **Current task:** F5 publication snapshot; later local work is validated but not yet published.
- **Baseline:** F9 implementation ff8072fe2137014737c81dbcecaf4754c418037b and completion 5cfc2e2c39a0aa2174b1c39fbf4ff7e8fb1b5ab5 verified published. Main e762cb48916f07fd939e9ad0ddb0b0d815f3305f unchanged; contract v0.2.0.
- **Green checks:** final lint, strict typecheck, production build; 22 native tests; eight production browser groups; both themes, roadmap/placement/tracker/dialog at 320/375/390/414/768/1440px; eight zero-violation axe scans; representative visual review; actual static Prism queries, milestone/application PATCH 200, CSV export 200 and application create 201. Mini-ring/full-ring and overlay final visual smoke passed in normal/reduced motion; two additional dialog scans passed.

## Resume here (exact next step)
1. User explicitly authorized continuous F5–F7, pausing only for Git input. Implementation is complete; do not repeat green checks absent source changes/failures. No F8.
2. Run chat outputs/Publish-F567.ps1 in regular Windows PowerShell. It verifies baseline/files, publishes F5, F6 and F7 as separate commits with checkpoint snapshots, pushes each, then publishes the SHA completion snapshot. Metadata deny ACLs and Windows credentials require user terminal.
3. If interrupted publication: inspect git status/log and the reported push failure; do not replay script blindly. Local commits remain intact. Finish pending pushes/checkpoints, verify public origin/frontend/codex equals local HEAD via outputs/Invoke-CareerLensGit.ps1, then pause before F8.
4. On user F8 authorization: read apps/extension/AGENTS, PROMPTS F8, DESIGN, PIPELINE and generated job/app schemas; implement extension only. Backend B7/B9 and real integration remain separate tracks.

## Task board
| Id | Task | Status | Commit |
|---|---|---|---|
| F1 | Scaffold/shell/client | done | 99a083e |
| F2 | Component kit | done | 82828dc |
| F3 | Onboarding/progress | done | 231329d |
| F4 | Dashboard/report/simulator | done | f129ef2 |
| F9 | Project quiz | done | ff8072f; checkpoint 5cfc2e2 |
| F5 | Roadmap/history | validated; publication pending | pending publication |
| F6 | Placement cell | validated; publication pending | pending publication |
| F7 | Tracker | validated; publication pending | pending publication |
| F8 | Extension | todo | |

## Implementation / next files
- F5: app/roadmap/page.tsx, components/roadmap/roadmap-screen.tsx, lib/score-history.ts, tests/score-history.test.ts and docs/plans/frontend-F5.md. Server-order deliverables, immediate local done state persisted by existing generated mutation, rollback/retry/lock; completion progress never changes score. History only completed returned samples; periods relative to latest sample, no averaging; report explanation links.
- F6: app/placement/page.tsx, components/placement/placement-screen.tsx, docs/plans/frontend-F6.md, compact rendering in components/career/score-ring.tsx. Catalog-driven cohorts/roles, independent query states, KPIs/definitions, band stack/histogram/missing counts, unverified/understanding/built-explained tables, student search/server-risk query and actual CSV Blob download. Returned counts/rates/statuses only, report links for readiness reasons; no private quiz data.
- F7: app/tracker/page.tsx, components/tracker/tracker-screen.tsx, lib/application-draft.ts, tests/application-draft.test.ts, docs/plans/frontend-F7.md. Native drag plus keyboard/touch select, optimistic local move with per-card lock/acknowledgment/rollback/retry; manual Radix dialog draft/validation/add lock. Missing match data remains unavailable. CSV export does not fabricate table contents.
- F9 remains complete. Cached quiz resume refreshes server timing; active card stays mounted across answer invalidation so exact retry snapshot survives. Quiz generation/grading/retake enforcement remains B9.
- Stubbed/fake: no new product fake data or client scoring. Scratch synthetic fixtures outside repo cover stateful behavior. Static Prism is stateless. B7 applications/cohorts and B9 quizzes are unrouted on current main; real integration is Phase 3. F8/settings beyond requested prompts not started.
- Dependencies/protected files: none added for F5–F7. Backend/data/contract/generated client/extension/root packages and lock unchanged. Only Codex web and own plans/progress/append-only handoff changed.

## Decisions
- Order F1 → F2 → F3 → F4 → F9 → F5 → F6 → F7 → F8. Latest user instruction overrides earlier pauses: continue F5–F7 until Git input is needed.
- User wants speed with value: batch independent reads/checks, scope validation to changes, avoid repeating green tests without cause. Keep executable checkpoints and conventional commits/pushes.
- DESIGN/design-refs lock Plus Jakarta Sans, themes/tokens, F2 components. Hallmark state/accessibility guidance applies; taste excludes dashboards/data tables/multistep product UI.
- Generated API shapes only; no scoring, inferred bands or invented resources. Milestone completion uses contract PATCH; re-scan measures score changes. Compact ScoreRing changes only sizes below 120 px; default 160 px presentation preserved.
- API summaries omit full reasons: history/placement link to actual evidence reports; aggregate and match explanations describe supplied data rather than inventing reasons.

## Gotchas
- Sandbox PATH/Path duplicates caused earlier git-remote-https crashes. Chat launcher normalizes PATH and pins installed Git/helpers/OpenSSL; public ls-remote works. Metadata index.lock/FETCH_HEAD deny ACLs and saved Windows credentials require normal user terminal; never repeat ACL fixes or use bypass metadata.
- F4 GitHub server-error retries: full fsck passed, later --no-thin succeeded; cause remains unproven. F567 publisher uses normal non-force --no-thin pushes.
- Next re-adds installed docs guidance to web AGENTS; preserve committed block. next-env unchanged after final build. Read installed guides before framework changes.
- Static Prism cannot prove persistence/backend scoring; stateful fixtures cover UI flows, Phase 3 verifies live integration. Axe is not a full manual audit.
- Dialog overlay uses existing --overlay token; score rings need compact typography for 72/88px sizes. Native drag is desktop; status select provides keyboard/touch equivalence.

## Commands and evidence
- Node24.19.0: C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe. pnpm10.12.3: chat work/tools/node_modules/pnpm/bin/pnpm.cjs; prepend runtime bin to PATH. Existing store C:/Users/User/Desktop/CareerLens/.pnpm-store.
- Web checks: pnpm --filter web lint; pnpm --filter web typecheck; pnpm --filter web build. Native: apps/web node --experimental-transform-types --import ./tests/register.mjs --test tests/api.test.ts tests/onboarding.test.ts tests/report-presentation.test.ts tests/quiz.test.ts tests/score-history.test.ts tests/application-draft.test.ts.
- Production web :3000; static Prism :4010. Chat work/browser_f567.cjs and f567-fixture.cjs cover states/themes; prism_f567.cjs tests actual HTTP. Tools/fixtures stay outside repo.
- Chat outputs/F567-browser-checks.json, F567-prism-check.json, eight F567-*-accessibility.json files, light/dark screen/dialog screenshots, export-smoke.csv, F567-progress-report.md, F5/F6/F7-plan.md, publication snapshots/script. F9 prior evidence retained.
