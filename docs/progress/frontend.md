# Progress — Frontend track

## Status
- **Track:** frontend; owns apps/web, apps/extension and frontend workspace files.
- **Branch / worktree:** frontend/codex; C:/Users/User/Desktop/CareerLens/careerlens-web
- **Last updated:** 2026-10-07 17:29 Asia/Dubai by Codex (GPT 6.1 Sol, user-selected).
- **Current task:** F1 implemented and validated; preparing implementation commit and publish checkpoint.
- **State:** in progress
- **Last green checks:** Latest main e762cb4 and initial frontend branch published; client regeneration without schema drift, client typecheck, web typecheck, production build and eight API transport tests passed. Final web lint/typecheck/build passed. Browser checks and visual review passed in both themes at 320/375/390/414/768/1440px.

## Resume here (exact next step)
1. Work only in C:/Users/User/Desktop/CareerLens/careerlens-web. Read AGENTS.md, apps/web/AGENTS.md, docs/DESIGN.md, docs/plans/frontend-F1.md, F1 in PROMPTS.md and the last five handoffs.
2. All F1 checks passed. Review git status and diff against origin/main, then make the F1 implementation commit with this snapshot and frontend handoff.
3. Publishing requires regular Windows PowerShell: git -C "C:\Users\User\Desktop\CareerLens\careerlens-web" push origin frontend/codex. Verify the public remote using the corrected launcher; do not retry Windows credentials from the sandbox.
4. After implementation push, record its SHA and mark F1 done in this file, commit that completion snapshot and publish it. Report F1 and pause before F2; resume only when the user asks.
## Task board
| Id | Task | Status | Commit | Notes |
|---|---|---|---|---|
| F1 | Scaffold, tokens, shell, client/hooks | doing | | All checks passed; publishing checkpoint remains |
| F2 | Component kit | todo | | Await F1 completion and user continuation |
| F3 | Onboarding + polling UI | todo | | |
| F4 | Dashboard + report + simulator | todo | | |
| F9 | Quiz screens | todo | | |
| F5 | Roadmap + history | todo | | |
| F6 | Placement cell | todo | | |
| F7 | Tracker | todo | | |
| F8 | Extension | todo | | |

## In-progress detail
- **Files touched:** apps/web configuration, global tokens/providers, sidebar/topbar/theme/profile, route shells, /dev/roles, lib/api operations/query keys/hooks/upload/transport, focused API tests; workspace dependency lock/config; F1 plan.
- **What works:** 29 operations and hooks use frozen generated paths. Eight native Node HTTP transport/poll/retry tests pass. Static Prism and production web run; browser acceptance and visual review passed.
- **Stubbed / fake:** TODO(progress) in components/layout/section-shell.tsx: dashboard/report/roadmap/tracker/placement/settings feature bodies are later prompts. Temporary roles page is a real API proof. No fabricated metrics or analyses.
- **Known failing checks:** None. Publishing is the remaining completion step.

## Decisions
- Prompt order F1 F2 F3 F4 F9 F5 F6 F7 F8; pause after every prompt. User later authorized F1 execution without another plan approval pause.
- Reviewed all supplied project Markdown and all current docs Markdown, including DESIGN and new backend prompt files after pulling B1-B6.
- Frozen v0.2.0 contract and P0/integration handoff supersede older archive examples. Run Prism without -d.
- Use official shadcn registry components/Radix, locked DESIGN palette and locally bundled Plus Jakarta Sans. Hallmark/taste apply to quality within dashboard scope.
- Exact DESIGN tokens preserved; named readable text foregrounds supplement them to meet contrast requirements.
- Root packageManager remains pnpm@10.12.3. Local tooling copy is in the chat work/tools directory.
- Preserve old unverified drafts in ../careerlens; none are merged into this worktree.

## Gotchas
- Codex Windows environment contains PATH and Path. Prepending only PATH did not repair Git credential-helper shell lookup; a ProcessStartInfo launcher normalizes them and pins installed Git/helper directories.
- Corrected launcher avoids git-remote-https crash. Sandboxed Windows Credential Manager still cannot authenticate; do not repeatedly retry authenticated Git here.
- User added safe.directory for this exact frontend worktree and signed in through the regular Windows terminal; initial branch push succeeded. Subsequent pushes may need the same regular terminal.
- Sandbox-safe fetch launcher: C:/Users/User/Documents/Codex/2026-10-07/install-these-two-skills-from-github/work/Invoke-CareerLensGit.ps1 (use -c credential.helper= fetch origin for public fetch).
- Official shadcn registry cn imports need their configured @/lib/utils alias. Registry components currently use radix-ui.
- tsx/os.userInfo and esbuild CLI hit Windows sandbox permissions; tests now use Node native TypeScript transform plus a local module-resolution hook. All eight pass.

## Blocked on
- No implementation blocker. Publishing later commits requires the user's Windows credential context if sandbox authentication remains unavailable.

## Environment
- API default NEXT_PUBLIC_API_URL=http://localhost:4010; development bearer dev from @careerlens/api-client.
- Mock: pnpm mock (static contract examples, no -d). Production preview: http://127.0.0.1:3000/dev/roles; started with pnpm --filter web start.
- Client: schema generated from contract v0.2.0; Next transpiles @careerlens/api-client.
- Node bundled 24.19.0; pnpm executable: chat work/tools/node_modules/pnpm/bin/pnpm.cjs (10.12.3).

## F1 validation evidence
- pnpm --filter web lint / typecheck / build: pass (final source); pnpm --filter web test: 8/8 pass.
- pnpm gen:client: pass; generated schema has zero content diff; API client typecheck: pass.
- Browser: roles/profile HTTP, Bearer dev 200 and missing bearer 401, six destinations, active navigation, persistent light/dark/system themes, mobile Escape/focus return and skip link: pass.
- Roles loading/empty/error/retry states: pass; no application console/runtime errors.
- Both themes at 320/375/390/414/768/1440px: no horizontal overflow or wrapped controls; screenshots visually reviewed. axe WCAG A/AA scans: zero violations; this is an automated check, not a full accessibility certification.
- Evidence and reusable Git launcher: C:/Users/User/Documents/Codex/2026-10-07/install-these-two-skills-from-github/outputs/. Browser harness is in chat work/browser_f1.cjs.