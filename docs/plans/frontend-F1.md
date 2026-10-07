# F1 plan — scaffold and shell

Planning baseline: `origin/main` at `e762cb4` (Claude B1–B6 merged), frozen contract `v0.2.0`.
Working directory: `C:\Users\User\Desktop\CareerLens\careerlens-web`, branch `frontend/codex`.
User authorized planning and execution on 2026-10-07. Finish F1 and pause before F2.

## Source review and coordination

- Reviewed the supplied project Markdown, including README, ROADMAP, PROMPTS, RUNBOOK, shared and nested AGENTS, design, pipeline, scoring, quiz, research, progress and handoff files. Read the four backend prompt files added by the latest pull.
- The GitHub repository supersedes the older outer Desktop copies and archived starter. The supplied archive and earlier unverified drafts remain in `../careerlens`; do not copy their API types or unfinished later-prompt views into this worktree.
- Fetch remote updates before resuming. Use `frontend/codex` exclusively; push every commit. Backend and integration progress/handoff files remain owned by their tracks.
- P0 handoff corrects the older mock commands: run static Prism **without `-d`**. No backend integration until Phase 3.
- Prompt order is **F1 → F2 → F3 → F4 → F9 → F5 → F6 → F7 → F8**. The user requires a report and pause after each prompt. Do not start parallel extension or later screen work.

## F1 acceptance criteria

1. Next.js App Router scaffold, strict TypeScript, Tailwind v4, shadcn/ui, Lucide, Recharts, Framer Motion, next-themes and TanStack Query installed with dev/build/lint/typecheck scripts.
2. Exact DESIGN light/dark variables exposed through Tailwind `@theme`; Plus Jakarta Sans; system theme default and persistent toggle setting `data-theme` on html.
3. Six-item sidebar with active indication, top bar, theme control and API-backed profile chip; accessible mobile navigation.
4. `lib/api/client.ts` wraps the existing workspace `createApiClient`; query/mutation hooks cover all **29 frozen operations**, using generated request/response types.
5. Temporary `/dev/roles` page renders real HTTP data from Prism with loading, empty and contract-error states.
6. Lint, typecheck, production build and client typecheck pass; browser checks demonstrate roles wiring, themes, navigation and responsive layout. Progress/handoff committed and pushed.

## Implementation steps

### 1. Scaffold and dependency boundary

- Preserve root workspace and `pnpm@10.12.3`; add only the web package and lockfile changes needed by F1. Pin resolved dependency versions in the lockfile.
- Create `apps/web/package.json`, `tsconfig.json`, `next-env.d.ts`, `next.config.ts`, `postcss.config.mjs`, `eslint.config.mjs`, `components.json` and `lib/utils.ts`.
- Set strict TypeScript, App Router and `transpilePackages: ["@careerlens/api-client"]`. Use an explicit ESLint script suitable for the installed Next version.
- Add Next/React, the mandated design/query libraries and a minimal shadcn foundation (button, dropdown, sheet and skeleton). Import actual accessible primitives instead of recreating their keyboard behavior.
- Use self-hosted Plus Jakarta Sans from a font package so production builds do not fetch Google Fonts. Retain the font license.

### 2. Tokens, providers and shell

- Create `app/globals.css`, `app/providers.tsx`, `app/layout.tsx`, `app/page.tsx`, `app/icon.svg` and shell components under `components/layout/`.
- Keep every supplied color, radius, shadow and spacing token. Add named foreground/focus tokens only when needed for the required 4.5:1 text contrast. No arbitrary colors in component markup.
- Use Plus Jakarta Sans, 24px/600 titles, 16px/600 card headings, 1.5 line height, 20px card radius, 12px control radius, 280px desktop sidebar and the 8pt grid.
- ThemeProvider uses `attribute="data-theme"`, default system, accessible light/dark/system menu and hydration-safe initial controls. QueryClient lives once per browser mount.
- Sidebar destinations: Dashboard, Report, Roadmap, Tracker, Placement cell, Settings. Report needs an analysis id: do not invent one. Until a profile analysis exists, provide an accessible unavailable state. Later F3/F4 will supply the real id.
- Create minimal route shells for sidebar navigation, including `/report/[analysisId]`; clearly record unfinished feature bodies as `TODO(progress)`. Root opens the dashboard shell. Full onboarding, score cards, charts, data views and settings actions belong to later prompts.
- Mobile uses a shadcn Sheet with focus return, Escape closing and labelled trigger. Include skip link, current-page semantics, visible focus and reduced-motion support.
- Get the profile chip from `GET /v1/me`; use honest loading/error fallbacks. Do not invent a name, score, photo or metric.

### 3. Generated API access and hooks

- Preserve `packages/api-client/index.ts` and the frozen YAML. Never hand-edit `schema.d.ts` or create duplicate API models.
- API base comes from `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:4010`; development uses the existing `Bearer dev` behavior. Distinguish a contract Error from transport/network failures.
- Group hooks by domain, share stable query keys, gate identifier-dependent queries, pass abort signals and invalidate affected caches after successful mutations.
- Retry transient read failures only; do not retry authorization/validation/rate-limit responses indiscriminately. Mutations do not silently retry.
- Analysis polling is every 2 seconds while queued/running and stops on done/failed. Quiz timing/result UI is later, but types must already include the frozen fields and result endpoint.
- Multipart upload uses FormData and a body serializer; browser sets the boundary. File adaptation is limited to the generated binary-string boundary. CSV export parses text rather than JSON; deletes tolerate 204.

| Domain | Operations |
|---|---|
| Meta | getHealth, listRoles, getMe |
| Profiles | createProfile, getProfile, updateProfile, deleteProfile, uploadDocument |
| Analyses | startAnalysis, listAnalyses, getAnalysis, simulateAnalysis, updateMilestone |
| Quizzes | createQuiz, getQuiz, answerQuizQuestion, submitQuiz, getQuizResult, listQuizzes |
| Jobs/applications | matchJob, listApplications, createApplication, updateApplication, deleteApplication, tailorResume |
| Cohorts | listCohorts, getCohortInsights, listCohortStudents, exportCohort |

- Frozen corrections: ProjectAudit.url, required progress/claimed/counted_in_score, verified_skills, QuizQuestion.time_remaining_s, 429 details.retake_available_at, roadmap PATCH and quiz result GET. No invented interview endpoint or more_commits simulation signal.
- Hooks for later tasks exist in F1 but do not imply those task screens or currently unrouted backend endpoints are finished.

### 4. Roles proof page and visual checks

- Create `app/dev/roles/page.tsx` using the actual listRoles hook; display supplied ids, names and required skill information. Include API-source indication on this development page, retry control, skeletons and an empty state.
- Use the reference Jomo dashboard (`8b1185229017577.685d1c673dd97.png`) for sidebar/topbar proportion, calm canvas and surface separation. Dark references inform charcoal surfaces, soft-square controls and restrained violet accents. Do not copy their names or data.
- Hallmark and design-taste-frontend support token discipline, specificity, accessibility and visual review. The locked DESIGN system and dashboard scope override marketing hero/theme/layout rules. No catalog palette, alternate font or marketing section is needed.
- Verify both themes at desktop and 390px, plus Hallmark's 320/375/414/768px widths; check keyboard navigation, menu focus, long labels, no horizontal overflow and theme persistence across reloads.

### 5. Validation and completion checkpoint

- Run `pnpm gen:client`; confirm regeneration does not drift from the frozen schema.
- Run client typecheck, `pnpm --filter web lint`, `pnpm --filter web typecheck`, `pnpm --filter web build` and meaningful focused transport/query tests (multipart, CSV/204/error handling, polling termination).
- Start static Prism on :4010 and Next on :3000. Verify authenticated roles 200, missing bearer 401, actual rendered roles, profile chip and client/server console output.
- Record the actual result of each check, including any limitation. Review the diff against `origin/main` for frontend ownership and secret exclusion.
- Update `docs/progress/frontend.md` after meaningful steps and append the final F1 handoff. Make a conventional implementation commit, then record its SHA in a small progress commit if necessary; push every commit.
- F1 can be marked done only when checks and runtime acceptance pass and commits are pushed. Report the result and pause before F2.

## Limit/model/context checkpoints

Before a usage/context cutoff, stop feature work, run available checks, record exact resume commands, unfinished files, TODO(progress), failures and decisions. Commit as `wip(web): checkpoint F1`, push and return Resume here. A new model reads progress, AGENTS, nested rules, last five handoffs and F1, verifies git/checks, and follows the user's latest authorization. Never mark partial work done.

## Ownership and exclusions

Expected changes: `apps/web/**`, root `pnpm-lock.yaml` and necessary frontend root package scripts, `docs/plans/frontend-F1.md`, `docs/progress/frontend.md`, `docs/handoff/frontend.md`. Generated schema may change only via the generator if explicitly justified.
No deletions. No edits to `apps/api`, `data`, contract, backend/integration logs, archive drafts or extension implementation. No secrets or environment files committed.
