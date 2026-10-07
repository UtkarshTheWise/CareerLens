# CareerLens roadmap

Three iterations, one contract:

```
Phase 0  Contract freeze ──────────────┐   (human + Claude Code, plan mode)
                                        ├─► Phase 1  Backend   — Claude Code  (apps/api, data/)
                                        └─► Phase 2  Frontend  — Codex        (apps/web, apps/extension) against Prism mock
                                                   │
                                        Phase 3  Integration — Claude Code (wires the two, fixes drift)
                                                   │
                                        Phase 4  Demo hardening — whole team
```

Backend starts first (as requested) and is the critical path; Codex can start as soon as the contract is frozen because it builds against the mock. Exact prompts for every task are in `PROMPTS.md` (task ids match).

Times assume a 24-hour build. **Check DataQuest's rules on pre-written code**: planning docs and the contract are usually fine to prepare in advance; application code usually must be written during the event.

---

## Priority (what to cut when time runs out)

| P0 (demo fails without it) | P1 (wins points) | P2 (only if ahead) |
|---|---|---|
| Resume + GitHub ingestion, claim verification with evidence links, deterministic JRS with breakdown, gaps, roadmap from catalogue, role-fit, cohort dashboard with seeded batch, **project quiz in verify mode** | Project quiz practice mode (interview prep), low-evidence flags with fixes, design-portfolio judging (needed for the designer demo persona), what-if simulator, consistency chart, score history, extension side panel (JSON-LD), tracker Kanban | Truthful tailored resume PDF, quick practice quiz in the extension, Codeforces stats, public proof card, Supabase auth |

---

## Phase 0 — Setup and contract freeze (H0 → H2)

Owner: human + Claude Code (plan mode). Prompt: **P0**.

- [ ] Personal GitHub repo created (Vercel Hobby can't deploy org repos); push this starter kit.
- [ ] Accounts and keys: AI Studio (18+ owner), Groq, GitHub PAT, Supabase project, Render, Vercel.
- [ ] Confirm Gemini model IDs and current free quotas in AI Studio; put them in `.env`.
- [ ] Confirm Codex access (CLI/IDE needs ChatGPT Plus or an API key) and model via `/model`.
- [ ] Claude Code reviews `contracts/openapi.yaml` against `docs/SCORING.md` + `docs/PIPELINE.md`, adds `examples` to key schemas so the Prism mock looks realistic, proposes changes.
- [ ] Human approves → contract tagged `v0.2.0` on `main`. **Frozen.**
- [ ] Claude Code creates root `package.json` + `pnpm-workspace.yaml` with `gen:client` script, generates `packages/api-client`, then hands root package files to Codex.
- [ ] `docs/progress/*.md` committed on `main` (each worktree inherits its file).
- [ ] Two worktrees: `backend/claude` (copy `.claude/backend.settings.local.json` → `.claude/settings.local.json` inside it) and `frontend/codex`.

**Exit check:** `npx @stoplight/prism-cli mock contracts/openapi.yaml -d` serves every path; `packages/api-client/schema.d.ts` exists.

---

## Phase 1 — Backend with Claude Code (H2 → H14)

Branch `backend/claude`. Each task = one prompt in `PROMPTS.md`, one commit, one HANDOFF entry.

| Id | Task | Est. | Done when |
|---|---|---|---|
| B1 | Scaffold FastAPI app, config, DB models, error handler, `/health`, `/v1/roles`, `/v1/me`, `check_contract.py` | 1 h | `check_contract.py` runs (failures expected for unbuilt routes are listed, not crashing) |
| B2 | `data/skills.yaml` (~60), `roles.yaml` (7), `resources.yaml`, tutorial/readme template lists + loaders + validation tests | 1 h | Every role skill exists in skills.yaml; every skill in roles has ≥ 2 resources |
| B3 | Ingest: upload endpoint, pdfplumber/docx text, PII stripper, LLM gateway (Gemini→Groq→Ollama, cache, retry), resume extraction | 1.5 h | Fixture resume → valid `ResumeProfile`; gateway falls back on simulated 429 |
| B4 | GitHub collector (GraphQL + trees, 202 retry, cache) + detectors + repo signals + rule flags | 2 h | Recorded fixture of a real public profile → detected skills + signals; tests offline |
| B5 | `scoring.py` exactly per `SCORING.md` + what-if + ≥ 25 unit tests | 1.5 h | Tests cover each component, reweighting, low-confidence cap, bands |
| B6 | Pipeline + analyses endpoints (202 + polling + stage status), project judging, roadmap planner, role-fit | 2 h | `POST /analyses` on demo profile reaches `done` with a full report |
| B7 | Jobs match, applications CRUD, cohorts (insights, students, CSV), `seed_demo.py` with 40 synthetic students | 1 h | Cohort insights return sensible distributions on seed data |
| B9 | Project Understanding Check (`docs/QUIZ.md`): key-file fetch, quiz generation with hidden answer keys, server-side timing, answers, batch grading, understanding → evidence effects + re-score, cooldown, `understanding_gap` flag, cohort understanding stats | 2 h | Verify quiz on a fixture repo: questions cite real lines; a strong fixture answer set → `demonstrated` and score rises; a weak set → flag + drop; skipping changes nothing |
| B8 | Hardening: contract check green, CORS for extension, Render deploy, keep-alive workflow, README run steps | 1 h | Deployed `/health` OK; `check_contract.py` exit 0 |

**Checkpoint H6:** B1–B4 merged to `main`; a real analysis runs to "detecting".
**Checkpoint H12:** backend feature-complete for P0 analysis + simulate + cohorts.
**Checkpoint H14:** project quiz (B9) and hardening (B8) done. Run B9 before B8 so the contract check covers the quiz endpoints.

---

## Phase 2 — Frontend with Codex (H2 → H14, in parallel)

Branch `frontend/codex`, `NEXT_PUBLIC_API_URL=http://localhost:4010` (Prism mock) until Phase 3.

The F-task estimates add up to ~16 h for a 12 h window. Run two Codex sessions in parallel (one on `apps/web`, one on `apps/extension`, same branch, different folders), and if you're still behind at H12, F7 and F8 slip into the Phase 3 window.

| Id | Task | Est. | Done when |
|---|---|---|---|
| F1 | Next.js scaffold, design tokens (light/dark) from `DESIGN.md`, app shell + sidebar, API client + Query hooks | 1.5 h | Theme toggle works; `/v1/roles` from mock renders |
| F2 | Core components: ScoreRing, KpiCard, SegmentedGauge, TrendCard, StackedBars, level pills, StageProgress, Why-popover | 2 h | `/dev/components` page shows all in both themes |
| F3 | Onboarding (name + 3 steps + upload) and analysis progress (polling) | 1.5 h | Flow completes against mock |
| F4 | Student dashboard + Evidence report (claims table, projects, flags) + what-if panel + per-project quiz buttons and UnderstandingBadge | 2.5 h | Readiness score and every breakdown component have a Why popover |
| F9 | Project quiz screens: intro, one-question QuizCard (code snippet with line numbers, countdown, paste disabled in verify, focus-loss count), practice feedback per answer, results page with score change and review links, quiz history | 2 h | Both modes complete against mock; timer and no-back-navigation work |
| F5 | Roadmap + score history | 1 h | Milestones render with resources and gains |
| F6 | Placement-cell page (KPIs, bands, histogram, missing skills, unverified rate, understanding summary + built-and-explained rate, table, CSV) | 2 h | Works for any cohort/role from mock |
| F7 | Tracker Kanban (drag between statuses → PATCH) | 1 h | Status persists via API |
| F8 | Chrome extension: side panel, JSON-LD → adapters → text fallback, match rings, save to tracker, options page | 2.5 h | Loads unpacked; works on a Greenhouse page against mock |

**Checkpoint H8:** F1–F3 done, screenshots in HANDOFF.
**Checkpoint H14:** all P0 screens + extension built against mock.

---

## Phase 3 — Integration with Claude Code (H14 → H18)

Branch `integration`, in the main checkout (which has no `settings.local.json`, so no deny rules). Prompts **I1–I4**.

| Id | Task | Done when |
|---|---|---|
| I1 | Plan-mode review: read HANDOFF, both diffs, list mismatches and open CCRs; propose merge order | Human approves plan |
| I2 | Merge both branches; regenerate client; run contract drift check; point web to `:8000`; fix mismatches (prefer backend side) | `check_contract.py` green, `pnpm build` green |
| I3 | End-to-end smoke: seed → onboarding → analysis → report → what-if → practice quiz → verify quiz (score changes) → roadmap → tracker → placement → extension on 3 real job pages; fix bugs | Smoke script + checklist pass |
| I4 | Fresh-context review subagent: correctness, requirement gaps vs problem statement, security (keys, CORS, PII) | Findings fixed or logged |

---

## Phase 4 — Demo hardening (H18 → H24)

- [ ] Warm the cache: run every demo analysis once so the live demo hits cache (no quota risk).
- [ ] Offline fallback: Ollama model pulled, `OLLAMA_URL` set, tested with Wi-Fi off.
- [ ] Ping Render and Supabase 10 min before judging; or run everything locally.
- [ ] Two demo personas: (1) student with strong GitHub but inflated skills list, (2) designer with portfolio and no GitHub — shows fairness.
- [ ] Quiz demo moment: pre-generate (cache) a verify quiz for persona 1's best project; answer it live on stage and show the claim upgrade from `moderate` to `strong` and the score change. Have a practice quiz ready as backup.
- [ ] Placement-cell story on the 40-student seed cohort.
- [ ] Record a 2-minute backup video.
- [ ] Pitch: problem stats (India Skills Report 2026: 56.35 % employability), prior art slide (be upfront about hiring-agent / GradPipe), four differentiators, live demo, roadmap.

---

## Risks

| Risk | Mitigation |
|---|---|
| Quiz grading is wrong or harsh | Python scores from key-point classification only; grader told to ignore language/fluency; low result is "review needed", never an accusation; retake with fresh questions |
| Gemini free quota exhausted (~20/day on Flash) | Flash-Lite for bulk, Flash only for judging; Groq fallback; cache everything; warm cache before demo |
| GitHub 60/hr unauthenticated limit on venue Wi-Fi | Server-side PAT (5,000/hr); cache 24 h |
| Agents drift from contract | Frozen contract, generated client, `check_contract.py`, CCR process |
| Agents edit each other's code | Deny rules in the backend worktree's `.claude/settings.local.json`; ownership in AGENTS.md; `git diff --stat` check before merge |
| Lockfile conflicts | Codex owns root lockfile; Claude only touches `apps/api/uv.lock` |
| Render cold start / Supabase pause | Local demo as primary; keep-alive pings |
| Job sites change DOM | JSON-LD first; LLM text fallback |
| An agent hits its usage/context limit mid-task | Progress file updated after every step + `wip` commits; any other model continues with the RESUME prompt (`PROMPTS.md`) |
| Codex not available on free plan | One teammate's Plus account, or Claude Code also does frontend tasks using the same prompts (ownership rules still apply by phase) |

---

## After the hackathon

1. Pilot with a VIT placement cell: correlate evidence scores with offers (the open validation question).
2. Supabase Auth with GitHub OAuth (user token → private repo evidence with consent).
3. Commit-level authorship (which files the student touched) for stronger `strong` evidence.
4. Code-similarity check against popular tutorial repos (Dolos-style fingerprints).
5. Recruiter-facing verified proof card.
