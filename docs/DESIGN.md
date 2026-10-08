# CareerLens design system — Carbon & Citron

The user-approved homepage prototype supersedes the earlier indigo/violet reference palette. Apply this system to the homepage, authenticated app and Chrome extension. Preserve every API workflow, explanation, accessibility feature and stored preference.

## Source of truth
apps/web/app/design-tokens.css and apps/extension/src/design-tokens.css contain identical semantic tokens. Never inline a second accent palette in product components.

| Token | Dark | Light |
|---|---|---|
| Canvas | #0c0e0c | #f2f0e6 |
| Surface | #151914 | #faf9f3 |
| Nested surface | #1e241b | #e9eadc |
| Selected surface | #262e21 | #dde2cb |
| Main text | #f2f0e6 | #1c2115 |
| Secondary text | #a6ad9e | #606650 |
| Accent | #d1d59c | #535f32 |
| Accent ink | #1c2115 | #faf9f3 |
| Structural border | #333b2e | #d2d6c4 |
| Control boundary | #77806a | #7a826b |

Dark is the new web default; retain Light and System options and existing saved preference. Status colours are restrained sage/ochre, with red reserved for errors/destructive actions. Pair every status with a label. Readable status/tint and chart tokens live in the token files. Structural borders are decorative; control boundaries and focus rings must remain perceivable.

## Rhythm and components
- Plus Jakarta Sans, locally packaged. Body 14–16px/1.6; page headings 28px/600 with -.045em tracking; card headings 16px/600; KPI 36px/600 with tabular numbers. Homepage retains its larger expressive display scale.
- 4/8px spacing grid. Cards 18px radius, controls 10px radius, labelled status tags 6px radius. Cards have 20–24px padding and 16–24px gaps. Flat surface layers with strokes; no decorative shadows, gradients or glows.
- Workspace sidebar 240px; sticky header 72px with modest blur. Navigation uses a quiet selected surface and citron text, and aria-current. Mobile navigation remains a keyboard-operable sheet.
- Buttons and ordinary form controls use 44px minimum height. Primary fills use accent with accent ink; secondary controls use surface and the control-boundary token. Clear hover, pressed, focus, pending, disabled and error states.
- Rings use 7px strokes and 400ms ease-out; honour reduced motion. The homepage example ring has no centre arrow. Real scores keep their central values and explanations. Segmented gauges, legends and charts use labelled semantic tokens.
- Popovers, sheets, dialogs, empty/error/loading states, tables, roadmap, tracker, quiz and extension share these surfaces. Keep useful density for data screens; do not turn them into marketing layouts.
- Code panels remain monospaced with line numbers and readable syntax. Preserve quiz timing, input/privacy constraints and returned-answer boundaries.

## Homepage and motion
Asymmetric copy/product-demo hero; explicit synthetic example; selectable evidence explanation; concrete roadmap milestone disclosure; five native FAQ disclosures; student sign-in through existing Google authentication. No separate placement-team entry or fabricated testimonials/statistics.

Hover/selection transitions 180–220ms, ease cubic-bezier(.22,1,.36,1). One-time section reveal 16px/550ms, progressive enhancement only. Product sheet gently straightens on pointer/focus. No infinite animation, number count-up, decorative floating badges or layout shifts. Reduce motion removes transitions and transforms.

## Product and acceptance rules
Readiness and components expose reasons; coverage explains its definition. No frontend scoring. Skipping a quiz never lowers a score. Preserve target-role filtering, mutation rollback, stale response cancellation, explicit active-tab extraction and genuine auth. Synthetic data appears only in the labelled homepage example and test fixtures.

Verify text contrast (4.5:1), keyboard focus, mobile 320/375/414px, tablet 768px, desktop 1440px, both themes, empty/error/loading states and reduced motion. Keep rings/charts accessible with textual summaries. Web lint/typecheck/build and extension typecheck/build/test must pass before publication.
