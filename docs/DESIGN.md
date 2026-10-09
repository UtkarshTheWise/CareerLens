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

## App screens (signed-in workspace)

The homepage language, tuned for data screens. Tokens do not change; the classes live in `apps/web/app/app-style.css` and the React primitives in `apps/web/components/layout/page.tsx`. `/dev/components` shows every one.

| Primitive | Use it for |
|---|---|
| `PageHeader` (`.eyebrow`, `.page-title`, `.lede`) | The one h1 of a screen, with optional actions. |
| `Section` (`.app-section`, `.section-title`) | A hairline-ruled block of a screen. Prefer it to nesting cards. |
| `Panel` (`.panel`, `.panel-label`, `.panel-footer`) | A flat surface for one idea: a score, a form, a result. Footer holds a muted label and a tabular value. |
| `Metric` (`.metric`, `.metric-unit`) | A big tabular number with a muted unit, for example `65 / 100`. |
| `StatusText` (`.status-text`, `.tone-text-*`) | Status as coloured text with a dot, always beside its label. Use the filled `.status-pill` only in dense table or kanban cells. |
| `SelectRowGroup` (`.select-row`) | A list where choosing a row explains it below (claims, skills, filters). `aria-pressed`, polite live region. |
| `Disclosure`, `.faq` | A `+` row that opens a region; native `details` for questions and troubleshooting. |
| `TextLink` (`.text-link`) | Inline links; external ones get an arrow and "opens in a new tab" for screen readers. |
| `.field`, `.field-label`, `.field-hint`, `.field-error`, `.chip` | Every input, select and textarea; 44px high, visible boundary and focus. |
| `Button size="lg" trailingArrow` | The one primary action of a screen (48px, arrow 24px from the label). |

Scale: page title 30/38, 36/44 from 900px; section title 22/30; section rhythm 32px, 40px from 1024px; panels 24px, 28px from 640px. Keep data density: the app has no marketing hero, no call-to-action band and no 104px header. Status is never colour alone. Separate with hairlines instead of nested bordered boxes. Hover styles apply only to fine pointers (`@media (hover:hover) and (pointer:fine)`); the one-time reveal (`useReveal`) is limited to read-only overview sections and is skipped under reduced motion.

## Terrain accents (colour on data screens)
The olive base is kept, and six earthy hues sit on top of it so score screens are not one grey-green: citron, sage, teal, ochre, clay and plum (`--hue-*` and `--hue-*-text` in both `design-tokens.css` files, which stay identical). Fills and rings meet 3:1 and the `-text` variants meet 4.5:1 on the surface in both themes.

- Set one `hue-<name>` class, then use `tint-card` (soft gradient wash, hue border and 3px top rule), `hue-chip`, `hue-dot`, `hue-bar`, `hue-rule`, `hue-inset` or `hue-text` from `app/app-style.css`. This is the one place a gradient is allowed; other surfaces stay flat.
- Meaning first: readiness ring and card follow the band (ready sage, developing ochre, not ready clay); coverage is teal; verified skills and milestones are citron; role fit is plum; skill gaps use a clay rule with the estimated gain in sage.
- The five score components keep the same order and hue everywhere (`GAUGE_HUES`): citron, sage, teal, ochre, clay.
- Colour never carries meaning alone: every status keeps its text label.
