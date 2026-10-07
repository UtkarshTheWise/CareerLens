# apps/web — frontend rules (owner: Codex)

Stack: Next.js (App Router) + TypeScript (strict), Tailwind CSS, shadcn/ui, lucide-react, Recharts, Framer Motion, next-themes, TanStack Query, openapi-fetch with types from `packages/api-client`.

## Rules

- Follow `docs/DESIGN.md` exactly: tokens as CSS variables, light + dark themes, Plus Jakarta Sans, components listed there.
- API access only via `createApiClient()` from `packages/api-client` (openapi-fetch typed with the generated `paths`), wrapped in TanStack Query hooks in `lib/api/`. No hand-written API types.
- Base URL from `NEXT_PUBLIC_API_URL`. Build first against the Prism mock (`:4010`).
- Analysis is async: `POST …/analyses` → poll `GET /v1/analyses/{id}` every 2 s until `done | failed`; show `StageProgress`.
- The readiness score and every breakdown component get a "Why?" popover rendering `ScoreComponent.reasons[]`. Coverage shows its definition.
- In development the client sends `Authorization: Bearer dev` (the mock rejects requests without it).
- Level/band colours come from tokens; always pair colour with a text label.
- Empty, loading (skeleton) and error states for every data view. Errors render the contract's `Error.message`.
- No business logic that duplicates the backend (no client-side scoring). The what-if panel calls `/simulate`.
- Routes: `/onboarding`, `/dashboard`, `/report/[analysisId]`, `/quiz/[quizId]`, `/roadmap`, `/tracker`, `/placement`, `/settings`.
- Quiz UI never shows or infers answers before the API returns them; verify mode enforces the timer and no-back rule client-side too (server is authoritative).
- Responsive down to 390 px. Charts get `aria-label` summaries.

## Checks

`pnpm --filter web lint && pnpm --filter web typecheck && pnpm --filter web build`
