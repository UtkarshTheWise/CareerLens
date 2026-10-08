# F2 plan — component kit

Baseline: frontend/codex at beacd4a; origin/main e762cb4. F1 implementation and completion docs are both verified published. User authorized F2 on 2026-10-07. Finish F2 and pause before F3.

## Scope and design read

Reading this as a reusable evidence-led dashboard kit for students and placement teams, using the locked DESIGN system and existing shadcn/Radix foundation. Hallmark component scope applies; taste's marketing-only patterns do not override dashboard requirements. Reviewed DESIGN, F2, shared/nested AGENTS and backend/integration/frontend handoffs. Latest public fetch has no newer main commits.

## Execution

1. Add the twelve F2 components under apps/web/components/career: KpiCard, ScoreRing, SegmentedGauge, TrendCard, StackedBars, LevelPill, BandBadge, EvidenceRow, FlagCard, MilestoneCard, StageProgress and WhyPopover. Share contract-derived types/formatting and token-based card/state helpers; add only necessary shadcn primitives.
2. Preserve exact DESIGN tokens. Supplement semantic readable foregrounds; use 20px cards, 24px padding, 16px gaps, 40px icon chips, 20px/1.75 icons and tabular KPI values. Rings animate stroke-dasharray over 800ms, honoring reduced motion. Charts use Recharts monotone lines, two series, highlighted point/tooltip and rounded emerald stacks.
3. Use generated schemas for bands, levels, claims, flags, milestones, stages and score reasons. Do not recompute scores, bands, coverage or estimated gains. Why popovers render API reason text/deltas and evidence references; coverage explains its definition. Missing data shows an honest empty state.
4. Build /dev/components showing every component, explicit synthetic fixtures, all level/band variants, loading/empty/error states, controlled milestone save states and all analysis stages. Reuse supplied frozen contract examples. Any illustrative history/cohort chart data is clearly marked preview-only. No later-prompt routes or live backend integration.
5. Verify lint, strict typecheck, production build and existing transport tests. Browser acceptance covers keyboard popovers/tabs, milestone checked/disabled/loading/error behavior, chart summaries/data alternatives, reduced motion, failed/done analysis stages, all twelve components and both themes at 320/375/390/414/768/1440px. Run axe scans and inspect screenshots. Review ownership diff.
6. Update frontend progress after meaningful steps; append handoff. Commit/publish implementation and completion checkpoint via the user's regular Windows terminal if sandbox credential isolation persists. Report F2 and pause before F3.

## Files

Create: apps/web/components/career/*.tsx, shared helpers, apps/web/app/dev/components/page.tsx and fixture data, necessary apps/web/components/ui primitives, this plan.
Modify: apps/web/app/globals.css for named semantic/chart tokens, app-shell title mapping for the preview, docs/progress/frontend.md, append-only docs/handoff/frontend.md. No dependency additions expected. No deletions or protected-path edits.

## Checkpoint

Before limits/model/context changes: run available checks, record exact remaining commands/files, list TODO(progress) and failures, commit wip(web) and publish. Keep progress under 150 lines. Never mark incomplete or unverified work done. Active worktree is C:/Users/User/Desktop/CareerLens/careerlens-web; never copy older drafts from ../careerlens. Static Prism runs without -d. Corrected Git launcher is in the chat outputs directory; authenticated pushes require normal Windows PowerShell.
