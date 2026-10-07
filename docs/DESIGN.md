# Design system (for Codex)

Derived from the reference shots in `design-refs/` (add the full folder there). Two references define the look:

- **Light mode**: the "Jomo" recruiting dashboard and the chart-card sheet. White rounded cards on a cool grey canvas, indigo/periwinkle accents, emerald greens for data, big donut rings with a centred number and label, smooth line charts with one highlighted point and a tooltip bubble.
- **Dark mode**: the inbox/CRM shots. Near-black canvas, charcoal cards, violet primary button, an orange→violet gradient on the *selected* list item, small yellow hashtag pills, segmented pill tabs, rounded icon-buttons in soft squares.

Never copy those products' names, logos or exact layouts. Use the tokens and patterns below.

---

## Tokens

Define as CSS variables in `apps/web/app/globals.css` and expose them to Tailwind v4 with an `@theme` block (`bg-surface`, `text-muted`, etc.; no `tailwind.config` file in v4). Same token names in the extension.

```css
:root {
  --bg: #F3F4F8;          /* canvas */
  --surface: #FFFFFF;     /* cards */
  --surface-2: #F7F8FC;   /* inputs, table header, nested panels */
  --border: #E5E7F0;
  --text: #111827;
  --muted: #6B7280;

  --primary: #4157E0;     /* indigo-blue (sidebar active, links, focus) */
  --primary-soft: #C9D0FF;/* periwinkle rings, chart secondary line */
  --primary-deep: #2E2A9E;/* dark arc of the gauge */

  --data-1: #0B6B4F;      /* deep emerald */
  --data-2: #0E9F6E;      /* emerald */
  --data-3: #A7F0D2;      /* mint */

  --success: #12A150;
  --warning: #F5A524;
  --danger:  #E5484D;
  --tag:     #FDE047;     /* yellow pill */

  --radius-card: 20px;
  --radius-control: 12px;
  --shadow-card: 0 1px 2px rgba(17,24,39,.04), 0 8px 24px rgba(17,24,39,.06);
}

:root[data-theme="dark"] {
  --bg: #0A0A0C;
  --surface: #141418;
  --surface-2: #1C1C22;
  --border: #2A2A32;
  --text: #F4F4F5;
  --muted: #A1A1AA;

  --primary: #7C3AED;     /* violet */
  --primary-soft: #A78BFA;
  --primary-deep: #5B21B6;

  --data-1: #34D399;
  --data-2: #10B981;
  --data-3: #065F46;

  --highlight-gradient: linear-gradient(135deg, #F97316 0%, #C026D3 55%, #6D28D9 100%);
  --shadow-card: 0 0 0 1px rgba(255,255,255,.04), 0 12px 32px rgba(0,0,0,.5);
}
```

Theme: follow `prefers-color-scheme` by default, with a toggle that sets `data-theme` on `<html>` (use `next-themes` with `attribute="data-theme"`, otherwise the dark selector won't match).

**Type**: Plus Jakarta Sans (Google Fonts, free). Page title 24/600, card title 16/600, KPI number 32–40/700 with tabular numerals, labels 12/500 muted uppercase-off. Generous line height (1.5).

**Spacing**: 8-pt grid; cards have 20–24 px padding; 16 px gap between cards; 280 px sidebar.

**Icons**: lucide-react, 20 px, 1.75 stroke, placed inside a 40 px soft-square chip (`bg-surface-2`, radius 12).

---

## Components (shadcn/ui as the base)

| Component | Pattern from the references | Used for |
|---|---|---|
| **KpiCard** | label top-left, icon chip top-right, big number, delta row `↑ +9.1% this week` (green/red) | Readiness, Evidence Coverage, Verified skills, Applications |
| **ScoreRing** | thick (12–14 px) SVG ring, rounded caps, `stroke-dasharray` animation (Framer Motion, 800 ms ease-out), centred number + small caps label; colour by band (danger / warning / success) | Job Readiness Score, Coverage, Match % |
| **SegmentedGauge** | multi-segment donut with legend rows (dot · label · %) underneath | Score breakdown A–E |
| **TrendCard** | smooth line (Recharts `type="monotone"`), two series (primary + primary-soft), one highlighted dot with a tooltip bubble, period tabs (Weekly / Monthly / Yearly) with an underline indicator | Consistency timeline, score history |
| **StackedBars** | rounded bars in `--data-1/2/3` | Cohort band distribution, skills by level |
| **EvidenceRow** | skill name · level pill · reason · link icons to evidence | Claims table |
| **FlagCard** | severity pill, reason, "How to fix" box, `+N pts` chip | Low-evidence project flags |
| **MilestoneCard** | order number, deliverable, resource links, effort, `+N pts`, done checkbox | Roadmap |
| **Kanban** | columns Saved / Applied / Interviewing / Offer / Rejected; cards with company, title, two mini rings | Tracker |
| **DataTable** | soft header (`surface-2`), avatar/initial chip, link column, row actions as icon buttons | Cohort students |
| **SidePanel (extension)** | dark-friendly, segmented tabs (Match / Gaps / Save), selected item uses `--highlight-gradient` in dark mode | Chrome side panel |
| **QuizCard** | one question per screen; code snippet with line numbers in a `surface-2` panel (mono font); countdown ScoreRing (verify); progress dots; MCQ options as large selectable cards; textarea for short answers (paste disabled in verify) | Project quiz |
| **UnderstandingBadge** | pill: Verified understanding (success) / Partial (warning) / Review needed (danger outline) / Not taken (muted) | Project cards, cohort table |
| **StageProgress** | vertical list of analysis stages with spinner → check | While polling an analysis |

Level pills: `strong` = success, `moderate` = primary-soft, `weak` = warning, `unverified` = muted outline, `missing` = danger outline. Always text + colour, never colour alone.

---

## Screens

1. **Onboarding** (3 steps): name + upload resume/LinkedIn PDF → GitHub username + portfolio URLs → target role. Then "Analyse".
2. **Analysis in progress**: StageProgress + skeleton cards.
3. **Student dashboard**: KPI row (Readiness ring, Coverage ring, Verified skills, Role fit) · "Why this score" breakdown · Consistency TrendCard · Top 3 gaps · next milestone.
4. **Evidence report**: claims table (filter by level), projects with subscores and flags, what-if simulator (toggle "add tests", "add CI", "deploy demo" → live score delta).
5. **Project quiz** (`/quiz/[quizId]`): intro (mode, number of questions, time per question, "answers graded on understanding, not English"), QuizCards, then results: quiz ScoreRing, UnderstandingBadge, per-question feedback with model answers and "view lines" links to GitHub, review topics, score change, retake time. Practice mode shows feedback after each answer.
6. **Roadmap**: milestone cards, progress, score-history chart.
7. **Tracker**: Kanban.
8. **Placement cell**: cohort picker + role picker, KPI row (students, median readiness, at-risk, median coverage), band StackedBars, histogram, top missing skills bar list, unverified-claim-rate table, understanding summary + built-and-explained rate per skill, students DataTable (with UnderstandingBadge) and at-risk filter, Export CSV.
9. **Settings**: theme, profile links, delete my data.

The readiness score and each breakdown component must have a "why" affordance (popover listing `reasons[]`); coverage shows its definition.

Accessibility: 4.5:1 contrast on text in both themes, focus rings in `--primary`, rings and charts labelled with `aria-label` summaries.
