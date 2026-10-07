# Progress — Frontend track

## Status
- **Track:** frontend; owns apps/web, apps/extension and frontend workspace files.
- **Branch / worktree:** frontend/codex; C:/Users/User/Desktop/CareerLens/careerlens-web
- **Last updated:** 2026-10-07 19:38 Asia/Dubai by Codex (GPT-6).
- **Current task:** F3 implementation validated; awaiting commit/publication from normal Windows terminal.
- **State:** F3 ready to publish; do not start F4
- **Last green checks:** final production build, lint and strict typecheck; 13 transport/validation tests; nine production browser groups; actual Prism DOCX/create/upload/start/done flow; both themes at 320/375/390/414/768/1440px across all wizard steps, progress and failure; ten current axe scans with zero violations. Final failure-copy checks pass.

## Resume here (exact next step)
1. Work only in C:/Users/User/Desktop/CareerLens/careerlens-web on frontend/codex. Read shared/nested AGENTS, DESIGN, root PROMPTS.md F3, docs/plans/frontend-F3.md and last five handoffs.
2. F3 source is finished and validated. No later prompt is started. F1/F2 and final F2 checkpoint d31554b are verified published. Public ls-remote confirms main e762cb4 (B1–B6) and frontend d31554b; no new main changes need merging.
3. Git add/fetch fail with Permission denied on ../careerlens/.git/worktrees/careerlens-web despite permission grants; existing Windows deny ACLs remain. Normal Windows terminal must stage the listed F3 paths, commit feat(web): add onboarding and analysis progress, and push origin frontend/codex. Do not alter ACLs or include unrelated files.
4. After user confirms publication, use chat outputs/Invoke-CareerLensGit.ps1 -c credential.helper= ls-remote origin refs/heads/frontend/codex; compare to git rev-parse HEAD and confirm clean status. Record that implementation SHA here and append publication handoff; user must commit/push this final docs snapshot too.
5. When both commits are verified published, report and pause before F4. On user continuation only: review F4 for dashboard, completed evidence report and simulator; reuse F2 kit and typed hooks. Order stays F4 F9 F5 F6 F7 F8, pausing after each.

## Task board
| Id | Task | Status | Commit | Notes |
|---|---|---|---|---|
| F1 | Scaffold, tokens, shell, client/hooks | done | 99a083e | beacd4a checkpoint published |
| F2 | Component kit | done | 82828dc | d31554b completion checkpoint published |
| F3 | Onboarding + polling UI | ready to publish | | All implementation checks pass; normal terminal Git needed |
| F4 | Dashboard + report + simulator | todo | | Await F3 publication/report and user continuation |
| F9 | Quiz screens | todo | | |
| F5 | Roadmap + history | todo | | |
| F6 | Placement cell | todo | | |
| F7 | Tracker | todo | | |
| F8 | Extension | todo | | |

## In-progress detail
- **F3 files:** app/onboarding/page.tsx; components/onboarding/onboarding-wizard.tsx; lib/onboarding.ts; tests/onboarding.test.ts; components/analysis/analysis-progress.tsx; app/report/[analysisId]/page.tsx; shell onboarding entry/title and active-link foreground; getAnalysis polling error stop; F3 plan/progress/handoff. Next dev generated an additive AGENTS.md docs-guidance block; installed framework guides were read. Final build restored next-env.d.ts unchanged.
- **What works:** three-step wizard, name/resume, PDF/DOCX up to 5 MB, optional LinkedIn PDF OR pasted text, optional GitHub username/web portfolio URLs, API role catalogue with loading/error/empty/retry, blur/step validation and focused associated errors. Inputs survive Back/Next; in-flight form locks and a synchronous latch prevents duplicate submissions.
- **API flow:** generated input types and existing hooks; create profile, upload files as real multipart File, start analysis, route to typed report ID. Within the mounted session retry reuses acknowledged profile and unchanged uploaded files; edited profile fields are PATCHed. After a LinkedIn PDF is saved its source mode stays locked (replacement PDF allowed) because contract has no document-delete operation.
- **Progress:** existing 2-second polling, StageProgress and skeletons, terminal done/failed stop, contract request errors pause polling with explicit retry, failed analysis can restart on saved profile/role. Completion confirms saved results without unexplained scores.
- **Stubbed / fake:** no mock data embedded in the onboarding/progress product. Default local backend is stateless Prism; staged/failing browser fixtures are synthetic and exist only in chat work. Completed evidence view has TODO(progress) for F4; remaining F1 feature bodies and other later routes remain their assigned prompts. Live backend integration remains Phase 3.
- **Known failing checks:** none. Only committing/publication is blocked by Windows Git metadata access and credential isolation.

## Decisions
- User resumed F3 after F2 completion report. Preserve strict prompt order and pause after each.
- DESIGN is locked: existing Plus Jakarta Sans, light/dark tokens, card geometry and F2 components. Hallmark interaction/state quality applies; taste marketing layouts do not apply to multi-step product UI. No new dependencies or client scoring.
- Required resume, optional GitHub/portfolio/LinkedIn, exactly one selected LinkedIn input source. No browser storage of personal entries or files; retry state lasts only while mounted. Resume parsing/type validation remains authoritative on the backend.
- HTTP query failures pause interval polling until explicit retry; transport-level bounded retries remain unchanged. Terminal analysis states stop polling.
- F4 owns the completed evidence report/dashboard/simulator. F3 shows completion only and keeps its TODO in source rather than product copy.

## Gotchas
- Sandbox PATH and Path duplicates previously crashed git-remote-https. Corrected ProcessStartInfo launcher normalizes child PATH and pins installed Git/helpers/OpenSSL; public ls-remote works. Authenticated Git still needs normal Windows Credential Manager context.
- Existing Windows deny ACLs now also block native index.lock and FETCH_HEAD writes. Specific repo/metadata grants were tried; no ACLs changed. Use normal Windows terminal for F3 commit and push.
- Next dev auto-appends its managed docs guidance to apps/web/AGENTS.md; keep this additive block and read installed guides. Build restores production next-env imports; do not hand-edit generated next-env.
- Shell active-link muted utility previously overrode selected-link foreground; conditional foreground now passes both theme axe scans on /report.
- Dev Strict Mode can abort an initial analysis request and issue another immediately. Production browser acceptance measures regular polling and terminal stop; actual interval remains 2000ms.
- Native tests use Node 22.16+ and tests/register.mjs; tested with bundled Node 24.19.0. No project test dependency was added.

## Environment and validation
- Static Prism :4010 (without -d); final production web :3000/onboarding. Source uses existing generated API client and hooks only. Contract/client/backend/data/extension/package/lock have zero F3 changes.
- Commands: pnpm --filter web lint; pnpm --filter web typecheck; pnpm --filter web build; pnpm --filter web exec node --experimental-transform-types --import ./tests/register.mjs --test tests/api.test.ts tests/onboarding.test.ts.
- Chat work/browser_f3.cjs: nine production acceptance groups (validation, source persistence, sequential multipart/retry, duplicate lock, profile PATCH, stage polling, done/failed stop/restart, catalogue states, request error recovery, both-theme responsive/axe). work/prism_f3.cjs verifies actual mock flow; work/final_failed_f3.cjs verifies final failure copy after final build.
- Evidence: chat outputs/F3-browser-checks.json, F3-prism-check.json, F3-final-failed-check.json, ten F3-*-accessibility.json files, 30 viewport screenshots, F3-plan.md and F3-progress-report.md. Automated scans do not replace full manual accessibility assessment.
- Runtime Node 24.19.0; pnpm 10.12.3 via chat work/tools/node_modules/pnpm/bin/pnpm.cjs. Scratch tools stay outside repository.
