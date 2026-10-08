# Carbon & Citron consistency

User authorises carrying the reviewed homepage design into the remaining frontend and pushing frontend/codex. Latest main is merged to retain Google authentication and backend integration; no backend or contract edits are authored here.

## Exact edit scope
- apps/web/app/{globals.css,design-tokens.css,providers.tsx}: shared palette, elevation, typography and dark default with light/system choices.
- apps/web/components/landing/{landing-page.tsx,landing-page.module.css}: port the reviewed interactive homepage; no arrow inside the example ring.
- apps/web/components/layout/{app-shell.tsx,brand-mark.tsx,theme-toggle.tsx,credit.tsx}: coherent navigation, mark and readable attribution.
- apps/web/components/auth/login-screen.tsx: same visual language, existing Google authentication unchanged.
- apps/web/components/ui/{button.tsx,tabs.tsx,sheet.tsx}: consistent control boundaries, touch sizes and motion.
- apps/web/components/career/{score-ring.tsx,segmented-gauge.tsx,kpi-card.tsx,../quiz/code-snippet.tsx}: slimmer evidence visuals, readable code and type.
- apps/extension/src/{styles.css,design-tokens.css,components.tsx}: matching palette, tab states and ring weight; activeTab/auth/extraction/storage untouched.
- docs/DESIGN.md, docs/progress/frontend.md, docs/handoff/frontend.md: approved design contract and checkpoint.

## Validation
Frozen dependency install; web lint/typecheck/build and all native frontend tests; extension typecheck/build/test; compare web/extension tokens; WCAG text contrast; browser desktop/mobile light/dark and key interactions. Existing functionality, score explanations, API calls, quiz timing and auth guards remain intact. Synthetic examples are explicitly labelled; no new dependencies.

- Screen-owned native controls in onboarding/settings/roadmap/placement/tracker/quiz/report and trend chart share control boundaries; there are no separate input/select/textarea UI files.

## Final scope additions
- apps/web/app/icon.svg uses the shared lens mark colours.
- apps/web/public/downloads/careerlens-extension.zip: CSS-only refresh preserves every other upstream archive entry. This avoids rebuilding production auth with missing environment values.
- Screen-owned control classes in onboarding/settings/placement/tracker/quiz/report; unchanged files need not appear in the diff. Existing quiz code theme already uses semantic variables.
