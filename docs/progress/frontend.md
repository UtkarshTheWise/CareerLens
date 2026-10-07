# Progress — Frontend track

## Status
- **Track:** frontend; owns apps/web, apps/extension and frontend workspace files.
- **Branch / worktree:** frontend/codex; C:/Users/User/Desktop/CareerLens/careerlens-web
- **Last updated:** 2026-10-07 18:48 Asia/Dubai by Codex (GPT 6.1 Sol, user-selected).
- **Current task:** F2 implemented and validated; implementation publication checkpoint next.
- **State:** in progress; do not start F3
- **Last green checks:** final web lint/typecheck/build; transport tests 8/8; all twelve components, controlled states, chart keyboard/data alternatives, normal/reduced motion, both themes, six viewport widths and axe scans passed. Main baseline e762cb4; F1 completion beacd4a published.

## Resume here (exact next step)
1. Work only in C:/Users/User/Desktop/CareerLens/careerlens-web. Read this snapshot, shared/nested AGENTS, DESIGN, docs/plans/frontend-F2.md, F2 in PROMPTS and the last five handoffs.
2. F2 implementation and runtime acceptance are complete. Review git status/diff; commit apps/web, F2 plan, this snapshot and the appended frontend handoff. Publish via regular Windows PowerShell: git -C "C:\Users\User\Desktop\CareerLens\careerlens-web" push origin frontend/codex.
3. Verify origin/frontend/codex matches the implementation SHA using the corrected public-fetch launcher. Record the SHA and F2 done in this snapshot, commit/publish the completion checkpoint. Report F2 and pause before F3.
4. F3 begins only on the user's continuation. Fetch main, review rules/DESIGN/F3/handoffs, plan onboarding/polling using existing typed hooks and StageProgress. Order remains F3 F4 F9 F5 F6 F7 F8; report and pause after each.

## Task board
| Id | Task | Status | Commit | Notes |
|---|---|---|---|---|
| F1 | Scaffold, tokens, shell, client/hooks | done | 99a083e | Implementation and beacd4a checkpoint published |
| F2 | Component kit | doing | | All checks pass; publication remains |
| F3 | Onboarding + polling UI | todo | | Await F2 report and user continuation |
| F4 | Dashboard + report + simulator | todo | | |
| F9 | Quiz screens | todo | | |
| F5 | Roadmap + history | todo | | |
| F6 | Placement cell | todo | | |
| F7 | Tracker | todo | | |
| F8 | Extension | todo | | |

## In-progress detail
- **Files touched:** apps/web/components/career, shadcn card/popover/tabs/checkbox, /dev/components page/fixture, semantic/chart tokens and preview shell title; F2 plan/progress/handoff.
- **What works:** twelve exported F2 components; API-derived reasons, bands, levels, flags, milestones and stages; Recharts trends/stacks with data alternatives; 800ms SVG rings, exact computed DESIGN shadows/radius/padding and non-looping reduced-motion spinner; safe evidence/resource links; controlled milestone save states; honest missing-data states.
- **Stubbed / fake:** /dev/components uses frozen synthetic contract examples and explicitly illustrative history/delta. Milestone preview is local state with no API writes/persistence. F1 section-shell TODO(progress) feature bodies remain later prompts. No F3/extension/client scoring implementation.
- **Known failing checks:** none. Publication is the remaining completion step.

## Decisions
- User resumed F2 on 2026-10-07. Strict order F1 F2 F3 F4 F9 F5 F6 F7 F8 with a pause after every prompt; no parallel later-prompt work.
- F1 implementation and completion checkpoint were verified published; fresh public fetch showed origin/main still e762cb4 (B1-B6). Frozen v0.2.0 contract unchanged.
- Reviewed DESIGN, F2, shared/nested rules and all three track handoffs. Prior review of all authored Markdown remains valid; no new remote docs arrived.
- Hallmark component scope and taste quality rules apply within the locked dashboard system. Preserve Plus Jakarta Sans and exact DESIGN colors/radii/shadows; named readable foregrounds supplement semantic colors.
- F2 adds no project dependencies. Official shadcn registry card/popover/tabs/checkbox use existing radix-ui and styling dependencies.
- Scores, bands, deltas, weights and gains come from supplied data. No frontend scoring or band inference. Readiness Why includes all five components; coverage includes its definition.
- Preserve old unverified drafts in ../careerlens; nothing copied from them.

## Gotchas
- Codex Windows environment has both PATH and Path; the corrected ProcessStartInfo launcher normalizes child PATH, pins installed Git/helpers and uses OpenSSL. Public Git operations avoid the earlier git-remote-https crash.
- Sandbox-safe public fetch: chat outputs/Invoke-CareerLensGit.ps1 -c credential.helper= fetch origin. Windows sandbox cannot access user Credential Manager; authenticated pushes require the regular Windows terminal. User already trusted this exact worktree and authenticated successfully.
- Native Node tests need Node 22.16+ (tested 24.19) and tests/register.mjs; tsx/os.userInfo failed under sandbox, so do not revert the runner casually.
- Browser checks wait for Radix closing animations and Recharts ResizeObserver dimensions before assertions. shadcn default shadow-sm was replaced with the DESIGN shadow-card; computed light/dark shadows match. Reduced motion limits CSS animation to one brief iteration. Dark moderate-pill foreground was corrected from 3.97:1 to an AA-passing named token, preserving the supplied violet background.
- Chromium capture-beyond-viewport can paint the translated, unfocused skip link in tall element captures. Computed live position remains -84px with no focus; normal viewport screenshots confirm it is offscreen. Use viewport captures for visual evidence, not this capture artifact.

## Blocked on
- No implementation blocker. Publishing commits needs the user's normal Windows credential context.

## Environment and validation
- Static Prism: pnpm mock (:4010, no -d); production web: pnpm --filter web start, http://127.0.0.1:3000/dev/components.
- F2 final lint/typecheck/build passed; eight existing HTTP transport tests passed. No API contract/client regeneration needed: protected paths and generated schema have no changes.
- Browser: all twelve components; five-component readiness reasons, signed deltas/evidence links, coverage definition, keyboard tabs/data table, milestone checked/saving/error/retry/disabled, queued/running/done/failed analysis, loading/empty/error views, reduced/normal motion: pass. No app console/runtime errors.
- Both themes at 320/375/390/414/768/1440px: no horizontal overflow or wrapped clickable text; viewport screenshots visually reviewed, plus component sections at mobile/desktop. Desktop axe WCAG A/AA: zero violations in both themes (not a full manual certification).
- Evidence: chat outputs/F2-browser-checks.json, F2-{light,dark}-accessibility.json, F2-*-viewport.png; harness chat work/browser_f2.cjs.
- Runtime Node 24.19.0; pnpm 10.12.3 via chat work/tools/node_modules/pnpm/bin/pnpm.cjs. Root packageManager unchanged.
