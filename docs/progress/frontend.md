# Progress — Frontend track

## Status
- **Track:** frontend; owns apps/web, apps/extension and frontend workspace files.
- **Branch / worktree:** frontend/codex; C:/Users/User/Desktop/CareerLens/careerlens-web
- **Last updated:** 2026-10-07 20:45 Asia/Dubai by Codex (GPT-6).
- **Current task:** F4 dashboard/report/simulator implemented and validated; normal-terminal commit/push pending.
- **State:** F4 validated, publication pending; pause before F9.
- **Last green checks:** final lint, strict typecheck and production build; 16 transport/onboarding/presentation tests; 13 production browser groups; actual Prism dashboard/report/createQuiz 201/simulate 200; normal/reduced motion and hydration; six zero-violation axe scans; both themes at 320/375/390/414/768/1440px; representative screenshots visually reviewed.

## Resume here (exact next step)
1. Work only in C:/Users/User/Desktop/CareerLens/careerlens-web on frontend/codex. Read shared/nested AGENTS, docs/DESIGN.md, root PROMPTS.md, this file and last five frontend/backend handoff entries.
2. F3 implementation 231329df7a3eed594af33919af2b07eb827a00dc is verified on GitHub. Public main remains e762cb48916f07fd939e9ad0ddb0b0d815f3305f; frozen OpenAPI v0.2.0, backend B1–B6. F4 source is finished; do not implement F9 yet.
3. User's regular Windows PowerShell must run: git -C "C:\Users\User\Desktop\CareerLens\careerlens-web" add -- apps/web docs/plans/frontend-F4.md docs/progress/frontend.md docs/handoff/frontend.md; git -C "C:\Users\User\Desktop\CareerLens\careerlens-web" commit -m "feat(web): add dashboard evidence report and simulator"; git -C "C:\Users\User\Desktop\CareerLens\careerlens-web" push origin frontend/codex. Run each command separately and stop on failure. Only frontend-owned paths are changed; no .env files are staged.
4. After the user confirms publication, verify local HEAD/status and public ls-remote origin refs/heads/frontend/codex with the chat outputs/Invoke-CareerLensGit.ps1 launcher. Record the matching implementation SHA here, mark F4 done and append a publication handoff. Publish that documentation checkpoint from normal PowerShell, verify it and pause before F9.
5. Only after user authorizes F9: read PROMPTS.md F9, docs/QUIZ.md §7, DESIGN and docs/plans/frontend-F4.md. Replace apps/web/app/quiz/[quizId]/page.tsx placeholder with intro/questions/results and report quiz history. Preserve contract, use generated hooks, and do not begin F5 until F9 report/pause.

## Task board
| Id | Task | Status | Commit | Notes |
|---|---|---|---|---|
| F1 | Scaffold, tokens, shell, client/hooks | done | 99a083e | beacd4a checkpoint published |
| F2 | Component kit | done | 82828dc | d31554b completion checkpoint published |
| F3 | Onboarding + polling UI | done | 231329d | Verified published; SHA recorded in this F4 continuation checkpoint |
| F4 | Dashboard + report + simulator | validated, publication pending | | All checks green; normal-terminal commit/push required |
| F9 | Quiz screens | todo | | Next prompt; user pause required |
| F5 | Roadmap + history | todo | | |
| F6 | Placement cell | todo | | |
| F7 | Tracker | todo | | |
| F8 | Extension | todo | | |

## In-progress detail
- **F4 source:** app/dashboard/page.tsx; components/dashboard/student-dashboard.tsx; report/{report-overview,evidence-report,project-card,what-if-panel}.tsx; lib/report-presentation.ts and tests; career understanding badge, optional second TrendCard series and hydration-safe ScoreRing; completed AnalysisProgress branch; listAnalyses stale-time control; quiz navigation destination. Existing onboarding Card padding corrected without changing flow.
- **Dashboard:** latest profile/analysis, readiness/coverage/verified count/top role KPIs, all five score reasons/evidence and effective weights, actual commit-count consistency chart, top three server gaps and next unfinished milestone. One polling observer; summaries requested fresh only after done. Months/years sum commit counts by week start, not inferred score history.
- **Report:** all-level claim filter/reasons/evidence links; code/design projects, appropriate returned subscores, flags/issues, descriptions, understanding labels; role fits/reasons; cap/confidence/data-gap notes. Loading/error/empty/missing-report and F3 terminal/restart behavior preserved. Summary errors have retry.
- **Simulator:** five requested missing code-project signals, typed simulateAnalysis, 350ms debounce, superseded-response protection, error/retry/reset, returned before/after/delta/bands and all component explanations. No client scoring, band thresholds or saved-score mutation.
- **Quiz handoff:** Practice/Verify call createQuiz, show contract errors/retake detail and route to /quiz/[quizId]?analysis=.... Both code/design checks supported. Minimal destination with return link is tracked TODO(progress) for F9; no questions, timers, quiz results or history are implemented in F4.
- **Stubbed / fake:** default backend remains stateless Prism; synthetic stage/design/error/race fixtures exist only in chat work. F2 /dev/components preview remains illustrative. Quiz destination is the F9 placeholder; roadmap milestone completion remains F5. Backend integration remains Phase 3. No synthetic dashboard/report product data.
- **Known failing checks:** none. Publication remains blocked in sandbox by existing Git metadata deny ACLs and credential isolation; user normal terminal works. F4 is not marked done until publication/SHA verification.

## Decisions
- Strict order is F1 → F2 → F3 → F4 → F9 → F5 → F6 → F7 → F8; report and pause after every prompt.
- DESIGN and design-refs lock Plus Jakarta Sans, light/dark tokens and F2 components. Hallmark interaction/state quality applies; taste marketing layouts exclude dashboards/multi-step UI. No new dependencies.
- All scores/levels/gains/counts/flags/quiz states come from generated API models. Presentation sorting/count rollups never recompute scores or infer bands.
- F3 acknowledged profile/file retry state remains mounted-session only; saved LinkedIn PDF source stays locked because no contract document-delete operation exists.
- HTTP query failures pause interval polling until explicit retry. Terminal done/failed stop polling. Dashboard passes its query to AnalysisProgress to avoid duplicate polling observers.
- Weekly consistency is the sole actual chart series; preserve F2 two-series caller compatibility. Next milestone is read-only until F5.

## Gotchas
- Sandbox PATH/Path duplicates previously crashed git-remote-https. Chat outputs/Invoke-CareerLensGit.ps1 normalizes child PATH and pins installed Git/helpers/OpenSSL; public ls-remote works. Authenticated pushes require normal Windows Credential Manager context.
- Existing Windows deny ACLs block index.lock and FETCH_HEAD writes despite specific grants. No ACL/global Git changes or bypass metadata. User normal Windows terminal must commit/push F4.
- Next dev re-adds its installed-docs guidance to web AGENTS.md; keep the committed block. Read node_modules/next/dist/docs guides for relevant APIs. Final build restores next-env.d.ts unchanged.
- Dev Strict Mode can abort/repeat the first request. Production checks confirm one 2000ms polling observer and terminal stop.
- Framer Motion reduced-motion preference differs during SSR. ScoreRing always starts identical SVG markup and settles with duration 0 when reduced; production hydration checks pass.
- Static Prism supplies generic simulation examples, not real deterministic gains. Its smoke validates actual HTTP contract wiring only.

## Environment and validation
- Static Prism :4010; production web :3000/dashboard. Protected backend/data/contract/generated client/extension/root packages/lock have zero F4 changes.
- Commands: pnpm --filter web lint; pnpm --filter web typecheck; pnpm --filter web build; pnpm --filter web exec node --experimental-transform-types --import ./tests/register.mjs --test tests/api.test.ts tests/onboarding.test.ts tests/report-presentation.test.ts.
- Chat work/browser_f4.cjs: 13 production groups including claims, scores/reasons, quiz modes/errors, simulation race/retry, no-profile/empty/error/running/failed, one-observer polling, six-width themes, six axe scans and F2 chart compatibility; no app console/runtime errors.
- Chat work/prism_f4.cjs: actual HTTP dashboard/report/createQuiz 201/simulate 200. work/motion_f4.cjs: normal/reduced ring geometry and clean hydration. Node native tests pass 16/16.
- Evidence: chat outputs/F4-browser-checks.json, F4-prism-check.json, F4-motion-checks.json, six F4-*-accessibility.json files, viewport/section screenshots, F4-plan.md and F4-progress-report.md. Axe does not replace a full manual accessibility audit.
- Runtime Node 24.19.0: C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe. pnpm 10.12.3: chat work/tools/node_modules/pnpm/bin/pnpm.cjs. Scratch tools stay outside the repository.
