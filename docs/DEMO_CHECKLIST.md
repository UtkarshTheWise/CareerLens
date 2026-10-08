# Demo checklist

What to click through before judging, in order. "CLI" marks what `apps/api/scripts/smoke_e2e.py` already proves
against a real running server (all 29 operations, responses checked against `contracts/openapi.yaml`); the
browser parts are yours to eyeball.

## Before you start (5 minutes)

- [ ] API up: `GET <api>/health` returns `200` (a Render free instance sleeps; the first call takes about a minute).
- [ ] `PLACEMENT_STAFF` on the API contains your coordinator account's email, so the cohort screens open.
- [ ] Web app points at the API (`NEXT_PUBLIC_API_URL`); the extension's API URL (Options) points at the same API.
- [ ] Supabase sign-in works (see `docs/AUTH_SETUP.md`): Google provider on, redirect URLs allow-listed.
- [ ] Gemini and Groq quotas are not exhausted. If they are, use the seeded demo profile and skip live analysis and quiz generation.
- [ ] Pre-generate the quizzes you will show (practice and verify, on your best repo), because generation costs LLM calls.
- [ ] Run the seed once for the cohort view: `cd apps/api && uv run python scripts/seed_demo.py` (40 synthetic students).

## The student path (web)

1. **Sign in** with Google. First visit lands on onboarding; later visits land on the dashboard. (CLI: token auth, 401s, one profile per account, isolation between users.)
2. **Onboarding**: name, GitHub username, target role, resume PDF/DOCX (try a 6 MB file to see the friendly "too large" message), optional LinkedIn text/PDF and portfolio links. Start the analysis. (CLI: profile, upload, analysis to `done`.)
3. **Progress**: stages advance (ingesting → extracting → collecting → detecting → judging → scoring → planning). A cold run takes about 1-2 minutes.
4. **Dashboard and report**: score ring with band and confidence, Evidence Coverage, five components each with reasons, skill claims with evidence links, project cards with flags and subscores. Every number can be explained. (CLI: shapes, components all carry reasons.)
5. **What-if**: toggle tests/CI/demo URL on a project and watch the projected score. (CLI: `simulate`.)
6. **Roadmap**: tick a milestone (it does not change the score), open its resources. Score history appears after a second analysis. (CLI: milestone PATCH, score unchanged.)
7. **Practice quiz** on a project: answer, see the model answer and the exact lines. Nothing changes the score. (CLI: practice flow, no score change.)
8. **Verify quiz**: intro screen, then one question at a time with a countdown; paste is blocked in the answer box. Submit. A weak result reads "understanding not demonstrated yet" with a review list, a roadmap milestone and a retake time; a strong result shows "understanding verified" and a higher score. (CLI: weak then strong round, `score_update`, flag, milestone, no answer keys before grading, focus-loss count for the student only.)
9. **Tracker**: save a job, drag it across the columns (or use the status menu). (CLI: create, move to applied, delete.)
10. **Placement view** (staff account only): cohort and role selector, bands, histogram, top missing skills, unverified-claim rates, understanding summary, students table with the at-risk filter, CSV download. Sign in as a normal student and confirm it says staff only. (CLI: insights, students, CSV; 403 for a student; no focus or answer data in any cohort response.)

## The extension

Build and load: `pnpm --filter extension build`, then `chrome://extensions` → Developer mode → Load unpacked → `apps/extension/dist`. Open Options, sign in with Google, **Fetch my profile**.

- [ ] **Greenhouse job page**: click the toolbar icon → side panel → Analyse. Expect title/company/skills read from the page, a keyword match and an evidence-backed match, matched/missing/unverified skills and a one-line summary. Save to tracker; it appears in the web tracker. (CLI: `matchJob` with listed skills, `matchJob` with page text only, create application.)
- [ ] **Lever job page**: same.
- [ ] **LinkedIn job page** (a single selected job, not the feed or a profile): same. Profiles and unselected listings are refused on purpose.
- [ ] Tailor (P2): from the web tracker, "Tailor resume" on a saved job with a description: bullets stay the student's own words, unsupported numbers are listed, nothing is invented. (CLI: `tailorResume`, rewrites that add a skill or number are rejected.)

## Say it out loud

- A weak quiz result never means "you didn't build this". The flag is `understanding_gap`, the copy says "not demonstrated yet", skipping a quiz never lowers a score.
- Nothing claims to detect AI-written text; the pitch is "checks your code, then checks that you can explain it".
- Resumes are stripped of names, emails, phones and links before any model sees them; demo data is synthetic.

## Not verified by a script

Browser rendering and accessibility (Codex ran axe and screenshots on the web app and extension against a mock), Google consent and the extension's `launchWebAuthFlow`, a real Render deploy, and current LinkedIn markup. Check these by hand once.
