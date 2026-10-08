# Progress — Frontend track

## Status
- **Track:** frontend; owns apps/web/apps/extension and frontend workspace files.
- **Branch / worktree:** frontend/codex; C:/Users/User/Desktop/CareerLens/careerlens-web.
- **Last updated:** 2026-10-08 Asia/Dubai by Codex (GPT-6).
- **Current task:** All five F5–F9 refinement implementations published; final SHA completion checkpoint being published. Pause for user after verification.
- **Baseline:** frontend/codex c1d608fb3962e3737ddc0a89fd4533ed06467378 verified published. Local main e762cb4; public main 622ea0b adds only the presentation. Contract v0.2.0 unchanged; no contract rebase/client regeneration needed.
- **F8 green checks:** strict typecheck and both Vite production builds; 20 native fixture/settings tests; genuine unpacked Chromium toolbar/side panel/activeTab/scripting/storage/HTTP; Match/Gaps/Save/options in both themes at 320/375/390/414/768px, eight zero-violation axe scans; screenshot review; retry/409/empty/duplicate/stale states; normalized llm posting saved with original URL; reduced motion; frozen offline install with every existing lock entry preserved.
- **Prior green checks:** F5–F7 final web lint/typecheck/build, 22 tests, production/browser/Prism checks; responsive themes and a11y; F9 quiz completed and published. No web source changed in F8.

## Resume here (exact next step)
1. All five implementations are published. Complete/verify the SHA checkpoint using chat outputs/Publish-Refinements.ps1. No repeat implementation checks needed.
2. Publisher preflights branch/baseline/SHA256 manifest, makes five focused commits and pushes each --no-thin without force, saves SHAs, appends publication handoff, then commits/pushes completion checkpoint. Its outputs/Refinement-published-commits.json permits resume after push failures.
3. After user reports done: read git log/status, verify public frontend/codex equals local HEAD and recorded checkpoint, verify five implementation SHAs and clean tree. Update only chat outputs/Refinement-progress-report.md with SHAs; no self-SHA repository commit.
4. Do not start integration, edit backend/contracts/generated schema, or repeat sandbox Git ACL/credential fixes. Phase 3 belongs to Claude.

## Published refinement commits
- F5 refinement: caf271b1b73f0ba071d3f4b485d46fb0db5c5d48
- F6 refinement: d11ee8a3cb77d6bb92d2695cb679a7d49fe157ad
- F7 refinement: 7ea7b8a181e143d5c03123fc81b3f368f6820d71
- F8 refinement: 6b51cb010599ac0d5983b8b9312b06a0bfcabd0b
- F9 refinement: 6847cc3c1ccae53125987617a343efddb10b636f

## Refinement detail (F5–F9)
- F5: next deliverable, All/To do/Done counts, estimated gains labelled, role selector isolates history, confirmed milestone mutations reconcile cache instead of permanently shadowing later updates.
- F6: student directory directly after KPIs, name/readiness/coverage sorting, 20-row pages, filter reset/result count, whole-cohort CSV scope, compact histogram and readable bands, six-skill previews/show all. Mobile controls and chart/table overflow scoped.
- F7: continuous five-stage board/grouped view, company/title search, update/deadline/company sorting, refresh, compact side-by-side rings, calendar deadlines and notes/details, focus restored after moves; query cache acknowledges updates and rollback clears overlays.
- F8: compact results header, actual description preview, setup shortcut, field/date validation; HTML paragraph boundaries, domain suffix boundaries, relative/tracking URL and selected LinkedIn matching, reject ambiguous/unrelated structured postings before DOM fallback.
- F9: compact question/result spacing, quiet 30/10-second timer announcements, complete progress dots, synchronous latest-input snapshot, readable returned choice text, practice/result focus, direct question review links. Verify/privacy/immutable retry guards preserved.
- Checks: web lint/typecheck/production build; extension typecheck/build; 28 web + 25 extension native tests; stateful original/new browser flows; genuine unpacked Chromium; light/dark six web widths (320/375/390/414/768/1440), five extension widths; 33 zero-violation axe reports; screenshot review and final mobile label/ring geometry checks; git diff --check.
- No new dependencies or backend/contracts/generated-client/root workspace changes. Synthetic fixtures remain scratch/test-only. Real backend/auth/persistence/idempotency/live-job end-to-end validation remains Phase 3; these checks do not certify it.

## Task board
| Id | Task | Status | Commit |
|---|---|---|---|
| F1 | Scaffold/shell/client | done | 99a083e |
| F2 | Component kit | done | 82828dc |
| F3 | Onboarding/progress | done | 231329d |
| F4 | Dashboard/report/simulator | done | f129ef2 |
| F9 | Project quiz | done | ff8072f; checkpoint 5cfc2e2 |
| F5 | Roadmap/history | done | 7b5123f24d8ca2ee835946300b275b1ede51bf5d |
| F6 | Placement cell | done | 71d29d12363cd49645ceffcb809d0a411fb4a056 |
| F7 | Tracker | done | c1cb8d5245ded875e6517c21b87be265cea3cf5a |
| F8 | Extension | done | f337cdd44b98e312ccb6696a430e11a9c215d95d |

## F8 implementation / next files
- apps/extension: MV3 manifest, three Vite entry points and separately built classic IIFE extractor; React panel/options; copied DESIGN token/font theme; Match/Gaps/Save, returned rings/levels/lists/summary; explicit application save with both API match scores.
- src/adapters: jsonld + linkedin/greenhouse/lever/workday/naukri/generic + shared/index. Arrays/@graph, strip description HTML, calendar deadline validation; selectors then visible main text <=20k/source llm. No inferred company/skills/metrics.
- src/browser.ts: active HTTP(S) job only, isolated scripting, original/current page identity validation and extractor result deletion. LinkedIn profiles and listings without an individual job/currentJobId are rejected before DOM reads. Panel invalidates/aborts on tab close/switch/navigation or profile/API change.
- src/settings.ts/options.tsx: storage.local only API URL/profile UUID/theme, default localhost8000, generated getMe button, theme system/light/dark, validation/loading/error states. No keys, persisted posting/results or production auth setup.
- src/api.ts uses generated createApiClient and contract models only; dev/local sends Bearer dev. Local API host permissions only localhost/127.0.0.1; remote APIs require extension-origin CORS. README contains load/reload/setup/limits.
- src/adapters/__tests__: four saved synthetic HTML snippets and 20 tests covering all adapters/JSON-LD/fallback/hidden content/size/eligibility/dates/settings. No product synthetic data.
- docs/plans/frontend-F8.md; own progress; append-only own handoff. Root lock adds extension importer/tooling only; baseline importer/package/snapshot values preserved exactly. Backend/data/contracts/generated client/root package/workspace/web unchanged.

## Prior implementation
- F5: roadmap/history screen and score-history helper/tests. Contract milestone mutation, immediate local state/rollback/retry/lock; returned history samples only; report explanation links.
- F6: placement screen, API cohorts/roles/students, returned KPI/bands/histogram/skills/understanding tables, actual CSV Blob export; no client scores. Compact F2 ScoreRing typography preserves 160px default.
- F7: tracker screen/application-draft helper/tests, native drag plus keyboard/touch status select, optimistic mutation/rollback/retry/lock; validated manual dialog, original returned match scores or unavailable.
- F9: project quiz remains complete. Server timing refresh, mounted active question and immutable retry snapshot; generation/grading/retake enforcement belongs to B9.

## Stubbed / fake / integration limits
- No runtime fake data or frontend scoring added. Scratch job HTML and local stateful API are synthetic test fixtures; real match scoring, backend persistence/auth and full web/extension integration are Phase 3.
- Live public Greenhouse and Lever extraction succeeded (200, source dom/jsonld, real descriptions). Two searched LinkedIn job URLs expired/redirected to listings; final guard rejects the redirect. Saved LinkedIn job fixture passed real unpacked injection. Recheck a current live individual LinkedIn posting in integration.
- Chrome store packaging/signing/publishing not requested. dist is generated and ignored; rebuild/load unpacked per extension README. Exactly-once create after a lost server acknowledgement needs backend idempotency absent from the contract; pending/acknowledged saves are locally locked.

## Decisions / gotchas
- Order F1 → F2 → F3 → F4 → F9 → F5 → F6 → F7 → F8. User wants speed/value: batch independent work and scope checks to changes.
- DESIGN locks Plus Jakarta Sans/tokens/themes. Hallmark states/a11y applied; taste excludes dashboards/multistep product UI. Ring wrapper named match-ring to avoid Tailwind's ring utility.
- Use explicit chrome.action.onClicked to open sidePanel synchronously within toolbar gesture: automatic openPanelOnActionClick failed to grant activeTab in the unpacked test. Never inject on toolbar open; only Analyse reads content.
- Unpacked service workers can retain old builds in reused Chrome profiles; reload extension and close old panel. Browser checks use fresh profiles. CDP toolbar action requires tab target and browser-level session; actual panel target attached directly (no Chrome API shims).
- Earlier duplicate PATH/Path Git crashes resolved by chat read launcher. Shared index.lock/FETCH_HEAD ACLs and Credential Manager isolation require normal user PowerShell for Git writes; never repeat ACL fixes or bypass metadata. Normal non-force --no-thin pushes used after prior GitHub server errors (cause unproven).
- New source EOF is one newline; publisher checks staged whitespace before commit. UTF-8/BOM publisher supports Windows PowerShell 5, reads UTF-8 templates and appends handoff without replacing previous entries.
- Next may update web AGENTS; preserve committed guide block. Static Prism is stateless; axe is not a full manual audit. No checks need repeating for SHA-only docs publication.

## Commands / evidence
- Node24.19.0 C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe; prepend bin to PATH. pnpm10.12.3 chat work/tools/node_modules/pnpm/bin/pnpm.cjs; existing store C:/Users/User/Desktop/CareerLens/.pnpm-store.
- pnpm --filter extension typecheck; pnpm --filter extension build; pnpm --filter extension test. Frozen offline install passed. Extractor dist/extractor.js is standalone IIFE; extension pages contain only packaged code/fonts under strict CSP.
- Chat outputs/F8-build-check.txt, F8-browser-checks.json, F8-supplemental-checks.json, eight F8-*-accessibility.json scans, light/dark panel/options screenshots, F8-live-extraction.json, F8-linkedin-live-check.json, F8-main-update-check.json, F8-progress-report.md and Publish-F8.ps1.
- Scratch harnesses work/browser_f8.cjs, f8-supplemental.cjs, f8-live.cjs use Chromium in work/browsers and disposable profiles; tests do not change production manifest or Chrome APIs. Six site adapters also have native unit coverage.
