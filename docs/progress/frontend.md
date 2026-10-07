# Progress — Frontend track

## Status
- **Track:** frontend; owns apps/web, apps/extension and frontend workspace files.
- **Branch / worktree:** frontend/codex; C:/Users/User/Desktop/CareerLens/careerlens-web
- **Last updated:** 2026-10-07 22:10 Asia/Dubai by Codex (GPT-6).
- **Current task:** F9 project quiz done; implementation ff8072fe2137014737c81dbcecaf4754c418037b verified published. F4 implementation f129ef2 and completion checkpoint f029713 verified published.
- **State:** F9 implementation published; final documentation checkpoint ready to publish. Pause before F5.
- **Last green checks:** F9 lint, strict typecheck, production build; 20 native tests; 13 primary and five supplemental browser groups; actual static Prism createQuiz 201/getQuiz/answer/submit/result 200; light/dark seven views at 320/375/390/414/768/1440px; 14 zero-violation axe scans; keyboard, normal/reduced motion, no hydration/runtime errors and representative visual review.

## Resume here (exact next step)
1. Work only in C:/Users/User/Desktop/CareerLens/careerlens-web on frontend/codex. Read this progress first, shared/web AGENTS, DESIGN, PROMPTS.md and latest frontend/backend handoffs.
2. F9 implementation ff8072fe2137014737c81dbcecaf4754c418037b is verified published on origin/frontend/codex; worktree was clean before this documentation update. All recorded checks passed. Public main remains e762cb48916f07fd939e9ad0ddb0b0d815f3305f; contract v0.2.0.
3. Publish only this final progress/handoff snapshot from normal PowerShell with docs-only commit and push --no-thin origin frontend/codex. Existing metadata ACLs/Windows credentials require user terminal. Verify local/remote SHA, then pause before F5; no new implementation checks needed for these docs.
4. User asked to speed up without losing value: batch independent checks, choose checks by changed behavior/risk and avoid repeating green checks without new changes or failures. Preserve checkpoints and prompt boundaries.
5. Only on user resume of F5: read its prompt, ROADMAP, DESIGN, relevant contract and installed Next docs; implement roadmap and score history. F9 quiz backend B9/Phase 3 integration remains separate.

## Task board
| Id | Task | Status | Commit | Notes |
|---|---|---|---|---|
| F1 | Scaffold, tokens, shell, client/hooks | done | 99a083e | beacd4a checkpoint published |
| F2 | Component kit | done | 82828dc | d31554b checkpoint published |
| F3 | Onboarding + polling | done | 231329d | Verified published |
| F4 | Dashboard + report + simulator | done | f129ef2 | f029713 completion checkpoint published |
| F9 | Quiz screens | done | ff8072f | docs/plans/frontend-F9.md |
| F5 | Roadmap + history | todo | | Pause before starting |
| F6 | Placement cell | todo | | |
| F7 | Tracker | todo | | |
| F8 | Extension | todo | | |

## In-progress detail
- **F9 source:** app/quiz/[quizId]/page.tsx; components/quiz/{quiz-screen,quiz-card,code-snippet,quiz-feedback,quiz-result,quiz-history}.tsx; lib/quiz.ts; tests/quiz.test.ts; quiz hooks, report history, syntax tokens and highlighter dependency.
- **Intro/resume:** create response seeds intro without first GET serving a question. Only unserved creations skip fetch; cached resumes fetch a fresh server timer before activating. GET receipt metadata uses monotonic time and structuralSharing false; focus refetch disabled.
- **Quiz:** one current server-unanswered question; line-numbered syntax snippet, native MCQ radios, 2000-char textarea, practice hints/feedback only. Verify subtracts elapsed monotonic time from time_remaining_s, auto-records at zero, blocks paste/back UI and deduplicates blur/visibility count. No grading inference.
- **Recovery:** synchronous answer/submit locks; pending answer keeps the card mounted. Exact retry snapshot reconciles prior accepted answers before re-POST. Final acknowledgment submits; error/result retry and empty/no-timing states remain explicit.
- **Result/history:** returned grade/key points/model answer/source links; understanding status; before/after/delta/reasons; strengths/review topics; server cooldown and 429 recovery, fresh retake. History follows project review and links to resume/results. Submit refreshes report/profile/me/cohort caches. Missing verify status is never labelled practice.
- **Dependencies:** prism-react-renderer 2.4.1 for required syntax highlighting; lock diff adds only highlighter and its @types/prismjs dependency. No unrelated upgrades.
- **Stubbed / fake:** none in F9 product code. Static Prism is stateless and lacks authored quiz examples; stateful flows use synthetic contract fixtures outside repo. Backend B9 must supply real generation, grading, timer/retake enforcement and score update. Other routes remain their future prompts.
- **Known limits:** anonymous mock/dev auth only; browser controls supplement server authority. Backend/data/contract/generated client/extension and unrelated root packages unchanged by F9.

## Decisions
- Strict order: F1 → F2 → F3 → F4 → F9 → F5 → F6 → F7 → F8; report and pause after each prompt.
- DESIGN/design-refs lock Plus Jakarta Sans, themes, tokens and F2 components. Hallmark informs interaction/state quality; taste excludes dashboard/multistep product layouts.
- Generated APIs supply scores/levels/flags/quiz states. No frontend scoring, band inference or invented resources/URLs.
- F9 requires prism-react-renderer for real syntax highlighting; code palettes use existing readable semantic tokens plus named code-warm token.
- Quiz answers/focus stay in student views only; no placement leakage. Low results use understanding not demonstrated yet; skip never lowers score.
- F3 acknowledged file/profile retry state is mounted-session only. LinkedIn saved PDF locks because contract has no document-delete endpoint. F4 simulator calls API; milestone persistence awaits F5.

## Gotchas
- Sandbox PATH/Path duplicates previously crashed git-remote-https. Chat launcher normalizes PATH and pins installed Git/helpers/OpenSSL; public ls-remote works. Never expose credentials.
- Existing Git metadata deny ACLs block index.lock/FETCH_HEAD despite grants; do not repeat ACL changes or use alternate metadata. User terminal commits/pushes.
- Two F4 pushes returned GitHub Internal Server Error after object upload; full local fsck passed. Later push --no-thin succeeded, cause unproven. Backup: chat outputs/F4-local-backup.bundle.
- Next re-adds installed-docs guidance in web AGENTS. Keep committed block. next-env.d.ts unchanged after production build.
- F9 cached create and resumed quiz must differ: WeakSet creation tag/WeakMap monotonic receipt exist only in memory, no answer persistence. structuralSharing false preserves receipt identity.
- Keep QuizCard mounted during pending answer/invalidation so retry latch and exact payload survive; do not replace it with a loading-only parent.
- Prism HTTP proves contract wiring, not real backend quiz logic. Axe does not replace a full manual accessibility audit.

## Environment and validation
- Static Prism :4010; production web :3000, built against mock. Scratch tools/scripts stay in chat work/ and evidence in outputs/.
- Commands: pnpm --filter web lint; pnpm --filter web typecheck; pnpm --filter web build; from apps/web: node --experimental-transform-types --import ./tests/register.mjs --test tests/api.test.ts tests/onboarding.test.ts tests/report-presentation.test.ts tests/quiz.test.ts.
- work/browser_f9.cjs: 13 groups covering creation, practice/verify, confidentiality, timer/timeout, paste/focus, cached resume, retry/lost acknowledgment, duplicates, final submission, history and empty/errors; ten axe scans and six widths per theme.
- work/supplemental_f9.cjs: verify question/results six widths and four axe scans; keyboard heading/radio behavior and textarea boundary; normal/reduced motion/hydration; result retry/missing understanding/429 cooldown.
- work/prism_f9.cjs: browser create intro/getQuiz plus actual direct answer/submit/result requests, all expected HTTP statuses.
- Outputs: F9-browser-checks.json, F9-supplemental-checks.json, F9-prism-check.json, F9-*-accessibility.json, light/dark viewport/section/motion screenshots, F9-plan.md and F9-progress-report.md.
- Node 24.19.0: C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe. pnpm 10.12.3: chat work/tools/node_modules/pnpm/bin/pnpm.cjs. Existing dependency store: C:/Users/User/Desktop/CareerLens/.pnpm-store.
