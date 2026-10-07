# CareerLens

**Evidence-based employability analysis for students and placement cells.**
Built for DataQuest 3.0 (VIT Chennai), problem statement DQWL.

CareerLens reads a student's resume, GitHub, portfolio links and LinkedIn export, checks every claimed skill against real proof of work, and returns an explainable **Job Readiness Score**, a skill-gap report, role-fit suggestions and a step-by-step roadmap. Placement cells get a batch view of the same data. A Chrome extension carries the verified profile onto job pages.

> Positioning line for judges: *Existing tools tell a placement officer how students score on tests. CareerLens tells them whether what students claim is backed by work they actually built.*

---

## 1. Critical analysis of the original idea

### Verdict

The core idea (verify claims against evidence) is right and maps exactly onto the problem statement. The draft prompt, though, spends most of its scope on the part of the idea that is already a commodity, and it under-delivers on three things the problem statement explicitly asks for.

### What's strong

- **Claim-vs-evidence verification** is the real gap in the market. None of the mainstream job-seeker tools (Jobscan, Teal, Simplify, Huntr, Rezi, Careerflow, Jobright, Enhancv, Kickresume) checks a claimed skill against code or commits. They all match keywords.
- **Remediation plans per flag** (not just a score) match the PS requirement for "actionable, explainable guidance".
- **Structured JSON output** from the LLM is the right instinct.

### What needs fixing

| # | Issue in the draft | Why it matters | Fix |
|---|---|---|---|
| 1 | No **placement-cell / batch dashboard** | The PS says "placement teams gain batch-level insights". Missing it costs marks directly. | Add a Cohort Insights view (section 3). |
| 2 | No **design portfolio** evidence (Behance, Figma) | Explicitly in the PS. Also the one area no competitor covers. | Link-based design evidence, weighted lower and labelled. |
| 3 | No **consistency-over-time** signal | PS: "how consistently they learn, build, and stay active". | Commit cadence from GitHub's contribution calendar. |
| 4 | One mega-prompt produces score + audit + resume + links in one JSON | Large nested schemas get rejected by Gemini's structured output, outputs are not reproducible, and the score can't be explained. | Split into small pipeline stages. **Compute the score deterministically** from signals; the LLM only extracts and judges. See `docs/PIPELINE.md`. |
| 5 | "AI-Slop" detector / `isAiSlop` / "Larping" / "Integrity (honesty) score" | AI-text detectors scored 25–56% on a 2026 resume dataset and misclassify non-native English writing. Accusing Indian students of "slop" on that basis is unfair and indefensible in front of faculty judges. | Rename to **Evidence Coverage**, **Unverified claim**, **Low-evidence project**. Flag *what is missing*, never *who wrote it*. |
| 6 | LLM generates upskilling URLs | LLMs invent URLs. | Curated `resources.yaml` catalogue; the LLM only picks from it. |
| 7 | "Tailor & Apply" resume rewriting | Competitors' AI tailoring invents metrics ("reduced latency by 67%"). That's the exact problem CareerLens claims to solve. | Tailoring may only reorder, rephrase and emphasise **verified** claims, and must flag any number without evidence. |
| 8 | The Chrome extension is "the core edge" | Simplify, Teal, Huntr, Careerflow and Jobright already ship free JD-scraping extensions with match scores. | Make the extension the *delivery surface* for the verified score ("72% keyword match, 40% evidence-backed"). Build it last. |
| 9 | `gemini-1.5-pro` / `gemini-2.5-flash` | 1.5 is retired, and 2.5 is closed to new projects since 18 Sep 2026. | Gemini 3.5 Flash-Lite / 3.8 Flash with a Groq fallback. Confirm model IDs in AI Studio. |
| 10 | `customApiKey` stored on the user profile | Plain-text key in a shared DB. | Keep BYO keys in the extension's local storage or env only. Never persist. |
| 11 | LinkedIn DOM scraping | LinkedIn's API exposes only name/headline/photo/email, and hiQ v. LinkedIn ended in an injunction against scraping. | Use the user's own LinkedIn **profile PDF export** or pasted text. |
| 12 | Data model has scores but no **evidence objects** or history | "Explainable" means every score component points to a source. Without history you can't show improvement. | `Evidence` records with URLs, `ScoreBreakdown` components, analysis history. See `contracts/openapi.yaml`. |
| 13 | Eight major features in 24 hours | Scope will collapse into eight half-features. | P0/P1/P2 cut list in `ROADMAP.md`. |

### Be honest with judges about prior art

"Resume + GitHub score" is not new on its own. HackerRank open-sourced **hiring-agent** (MIT, ~7k stars) that parses resumes, enriches with GitHub, checks authorship and originality and outputs explainable scores. GradPipe (2025 startup) does a 0–100 resume+GitHub score. Hackathon projects (RashDev at FOSS Hack 2026, Devpost "Verify") do similar things. Say this up front, borrow hiring-agent's authorship-threshold idea openly, and show what none of them do (next section).

---

## 2. What makes CareerLens different

| | Keyword ATS tools (Jobscan, Teal, Simplify…) | GitHub scorers (hiring-agent, GradPipe, GitRoll) | Indian placement platforms (Superset, PlacementPreparation.io, Mettl, Unstop) | **CareerLens** |
|---|---|---|---|---|
| Checks claims against work | No | Partly (category level) | No (tests only) | **Per claim, with links** |
| Checks the student can explain their own code | No | No | Generic aptitude/coding tests | **Quiz generated from their repo** |
| Explainable score breakdown | No (opaque %) | Partly | Partly | **Every point traced to a signal** |
| Design portfolios | No | No | No | **Yes (link-based)** |
| Learning consistency over time | No | Partly | No | **Yes** |
| Student-facing roadmap | Generic | Limited | Test prep | **Tied to each gap** |
| Batch view for placement cell | No | No | Yes (test-based) | **Yes (evidence-based)** |
| Refuses to invent claims when tailoring | No | n/a | n/a | **Yes** |

The five differentiators to put on a slide:

1. **Per-claim proof links.** "Docker → `repo/infra/Dockerfile`, 11 authored commits" or "Unverified".
2. **Multi-modal evidence**, including design work, so designers and PMs aren't scored as failing developers.
3. **Explainable, deterministic score** built from published signals (repo hygiene, CI/tests, commit consistency, authorship share, originality).
4. **Project Understanding Check.** A quiz generated from the student's *own* files ("what happens in `update_stock()` when two requests arrive together?") that doubles as interview prep and raises or lowers the evidence behind each claim. Claimed → built → explained.
5. **Cohort view** for the placement officer: which claimed skills in a batch are actually backed by work, and explained by the student.

---

## 3. Feature set

### P0: must ship (covers every PS requirement)

1. **Ingestion**: resume PDF/DOCX, GitHub username (OAuth optional), LinkedIn PDF export or pasted text, portfolio/design URLs, target role.
2. **Evidence engine**: deterministic detectors scan GitHub repos for skill evidence (dependency manifests, file types, configs), authorship share, forks, templates, tests, CI, README quality, commit cadence.
3. **Claim verification**: each resume skill gets `strong / moderate / weak / unverified` with evidence links and a one-line reason.
4. **Job Readiness Score** (0–100) per target role with a component breakdown and "why" text (spec in `docs/SCORING.md`).
5. **Skill gap report**: required-for-role vs verified vs claimed-only vs missing.
6. **Roadmap**: ordered milestones, each tied to a gap, with curated resources and an estimated score gain.
7. **Role-fit**: top 3 roles from a curated role catalogue, with reasons.
8. **Cohort Insights** (placement cell): readiness distribution, top missing skills, unverified-claim rate per skill, at-risk list, CSV export. Seeded with synthetic students for the demo.
9. **Project Understanding Check: verify mode** (`docs/QUIZ.md`): 6 timed questions generated from the student's own repo (code-reading MCQs on their snippets, plus architecture / design-decision / debugging / extension short answers). Graded against a hidden answer key. `demonstrated` upgrades evidence; `not_demonstrated` raises an `understanding_gap` flag with a review list and retake. Never labelled as "didn't build it"; skipping is never penalised.

### P1: added features that strengthen the pitch

10. **Project Understanding Check: practice mode** (interview prep): untimed, hints, instant feedback with model answers linked to the exact lines in their repo.
11. **Low-evidence project flags** (replaces "AI-slop"): single-commit dumps, unmodified forks, default framework READMEs, tutorial-name matches, thin API wrappers, descriptions with no metrics or architecture. Each flag comes with a fix.
12. **What-if simulator**: "Add tests + CI to repo X → +6 points" (recompute the deterministic score with a hypothetical signal).
13. **Re-scan and progress history**: score over time, proving the roadmap works.
14. **Chrome extension side panel**: reads JobPosting JSON-LD (DOM fallback), shows keyword match *and* evidence-backed match, saves to tracker.
15. **Application tracker** (Kanban) fed by the extension.

### P2: only if time remains

16. Truthful tailored resume (reorder and rephrase verified claims, never add) rendered with `@react-pdf/renderer`.
17. Quick practice quiz from the extension: 3 questions on the project most relevant to the job on screen.
18. Codeforces public API stats as an extra evidence source.
19. Shareable public "proof card" for a student.

### Deliberately cut

- Auto-apply / autofill (crowded, and ATSs deprioritise bulk applications).
- AI-written-text detection (unreliable and biased).
- Scraping LinkedIn pages.

---

## 4. Architecture

```
            ┌──────────────────────────── apps/web (Next.js, Codex) ───────────────────────────┐
            │ Dashboard · Report · Project quiz · Roadmap · Tracker · Cohort Insights          │
            └───────────────┬──────────────────────────────────────────────▲───────────────────┘
                            │ typed client generated from contracts/openapi.yaml
 apps/extension (MV3, Codex)│                                              │
 side panel ── JobPosting ──┤                                              │
                            ▼                                              │
            ┌──────────────────────────── apps/api (FastAPI, Claude Code) ─┴───────────────────┐
            │ 1 Ingest   resume → text (pdfplumber/python-docx), LinkedIn PDF, URLs            │
            │ 2 Extract  LLM → ResumeProfile JSON (small schema)                               │
            │ 3 Collect  GitHub GraphQL → repos, languages, calendar, manifests, file tree     │
            │ 4 Detect   deterministic skill detectors + repo-quality signals (no LLM)         │
            │ 5 Judge    LLM → per-project judgement on descriptions vs evidence (small schema)│
            │ 6 Score    deterministic Job Readiness Score + breakdown (no LLM)                │
            │ 7 Plan     LLM picks roadmap items/resources from curated catalogues             │
            │ 8 Persist  Supabase Postgres (+ cache of every LLM/GitHub call)                  │
            │ Quiz       on demand: repo files → LLM questions + hidden key → LLM grades →     │
            │            Python scores → understanding → re-run step 6                         │
            └──────────────────────────────────────────────────────────────────────────────────┘
               LLM gateway: Gemini → (429) Groq → (offline) Ollama      PII stripped before LLM
```

Long analyses run as a background job: `POST /v1/profiles/{id}/analyses` returns `202` with an id, and the UI polls `GET /v1/analyses/{id}`.

Details: `docs/PIPELINE.md` (stages + LLM prompt templates), `docs/SCORING.md` (formula) and `docs/QUIZ.md` (Project Understanding Check).

---

## 5. Zero-cost stack (checked October 2026)

| Layer | Choice | Free limit / gotcha |
|---|---|---|
| Backend | **FastAPI** (Python 3.12, uv) | Run locally for dev and demo; deploy to **Render free** (sleeps after 15 min idle, ~1 min cold start, so hit `/health` before judging). |
| Frontend | **Next.js** (App Router, TS, Tailwind, shadcn/ui, Recharts, Framer Motion) on **Vercel Hobby** | 4.5 MB request body (upload resumes straight to the API or Supabase Storage); **Hobby can't deploy repos owned by a GitHub org** — use a personal repo. |
| Extension | Chrome **MV3** + Vite + React, `sidePanel` API | Load unpacked for the demo; `sidePanel.open()` needs a user gesture. |
| DB / Auth / Storage | **Supabase Free** | 500 MB DB, 1 GB storage, 50K MAU. **Pauses after ~7 days idle**: add a daily GitHub Actions ping. |
| Primary LLM | **Gemini** 3.5 Flash-Lite (bulk) / 3.8 Flash (judgement) via `google-genai` | Free quotas are no longer published (estimates: ~500/day Flash-Lite, ~20/day Flash). Check AI Studio. **Free-tier data may be used for training, users must be 18+**: strip PII, use synthetic resumes for the demo. `temperature` is deprecated on the newest models. |
| Fallback LLM | **Groq** `openai/gpt-oss-120b` (strict `json_schema`) | 30 RPM, 1,000 req/day, 8K tokens/min. No streaming with structured output. Llama 3.x is gone from free. |
| Offline LLM | **Ollama** (e.g. a small Qwen/Llama) | Supports JSON-schema output locally; demo-day insurance. |
| GitHub data | **GraphQL v4** with a token | Unauthenticated REST is 60 req/hr **per IP** (a hackathon Wi-Fi burns it in minutes). Use a PAT on the server (5,000/hr) or the user's OAuth token. Stats endpoints return 202 while computing: retry. |
| Resume parsing | **pdfplumber** (MIT), python-docx | Avoid PyMuPDF (AGPL) unless you accept the licence. |
| Code similarity (optional) | Simple fingerprinting / Dolos ideas | No off-the-shelf tutorial-clone detector exists; we use heuristics. |
| PDF output (P2) | `@react-pdf/renderer` in the web app | Avoid Puppeteer on Vercel (bundle limit). |
| Coding agents | Claude Code (backend), Codex (frontend) | **Codex CLI/IDE needs ChatGPT Plus or an API key**; the free plan only has limited desktop-app access. Confirm the model with `/model`. |

**Not free anymore (don't plan around them):** Cerebras free tier (ended 16 Jul 2026), Koyeb free (ended Feb 2026), Fly.io (trial only), Hugging Face Docker Spaces (paid), Render free Postgres (expires in 30 days). Behance API is unavailable; Figma's free-seat REST quota is 20 calls/month; Dribbble only returns your own shots.

---

## 6. Repository layout and ownership

```
careerlens/
├── AGENTS.md                 # shared rules — read by Codex AND Claude Code
├── CLAUDE.md                 # imports AGENTS.md + Claude-only rules
├── README.md / ROADMAP.md / PROMPTS.md
├── .claude/
│   ├── settings.json         # shared allow-list, blocks reading .env, registers the progress Stop hook
│   ├── hooks/require-progress.sh     # blocks ending a session with unrecorded changes
│   ├── backend.settings.local.json   # copy into the backend worktree as settings.local.json
│   └── frontend.settings.local.json  # only if Claude Code ever builds frontend
├── contracts/
│   └── openapi.yaml          # SINGLE SOURCE OF TRUTH — frozen after Phase 0
├── packages/
│   └── api-client/           # generated from the contract; never hand-edited
├── apps/
│   ├── api/                  # FastAPI          — owner: Claude Code
│   ├── web/                  # Next.js          — owner: Codex
│   └── extension/            # Chrome MV3       — owner: Codex
├── design-refs/              # UI reference shots (add the rest of your folder here)
├── data/                     # skills.yaml, roles.yaml, resources.yaml, seed cohort — owner: Claude Code
└── docs/
    ├── PIPELINE.md           # analysis stages + LLM prompt templates
    ├── SCORING.md            # readiness formula
    ├── QUIZ.md               # Project Understanding Check (quiz) spec
    ├── DESIGN.md             # UI tokens & component rules (light + dark) from the reference shots
    ├── HANDOFF.md            # append-only log between agents
    ├── progress/             # backend.md, frontend.md, integration.md — live state per track for model hand-off
    └── RESEARCH.md           # market, free-stack and agent-coordination research
```

The coordination flow (contract → backend ∥ frontend → integration) and copy-paste prompts for each step are in **`PROMPTS.md`**. The schedule is in **`ROADMAP.md`**.

---

## 7. Getting started

### Accounts (all free)

1. **Google AI Studio** API key (owned by a teammate aged 18+).
2. **Groq** console API key.
3. **Supabase** project (enable the GitHub auth provider later if you want OAuth).
4. **GitHub** fine-grained personal access token, public-repo read only.
5. **Vercel** and **Render** connected to a *personal* GitHub repo.

### Environment (`apps/api/.env`, never committed)

```bash
GEMINI_API_KEY=
GEMINI_MODEL_FAST=gemini-3.5-flash-lite   # confirm exact IDs in AI Studio
GEMINI_MODEL_SMART=gemini-3.8-flash
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b
OLLAMA_URL=http://localhost:11434          # optional
GITHUB_TOKEN=
DATABASE_URL=postgresql+psycopg://...      # Supabase connection string (or sqlite:///./dev.db locally)
SUPABASE_JWT_SECRET=                       # optional; DEV_AUTH=1 skips auth locally
DEV_AUTH=1
CORS_ORIGINS=http://localhost:3000        # extension origins are allowed by regex in code
```

### Run (once the agents have built it)

```bash
# backend
cd apps/api && uv sync && uv run fastapi dev app/main.py        # http://localhost:8000/docs

# mock API for frontend work before the backend exists
npx @stoplight/prism-cli mock contracts/openapi.yaml -p 4010

# typed client
npx openapi-typescript contracts/openapi.yaml -o packages/api-client/schema.d.ts

# frontend
cd apps/web && pnpm i && pnpm dev                                # http://localhost:3000
# NEXT_PUBLIC_API_URL=http://localhost:4010 (mock) or :8000 (real)

# extension
cd apps/extension && pnpm i && pnpm build   # chrome://extensions → Load unpacked → dist/
```

---

## 8. Privacy and fairness

- Strip names, emails, phone numbers and addresses from text before any LLM call (free Gemini tier may use inputs for training).
- Use synthetic or consenting resumes in the demo.
- Never label a student's writing as AI-generated. Flags describe missing evidence and how to add it.
- A weak quiz result means "understanding not demonstrated yet", never "you didn't build this". Quiz answers are graded on concepts, not English fluency, and the placement cell sees only the status, not the answers.
- Design and non-code roles are scored on the evidence sources that make sense for that role (see `docs/SCORING.md`); missing GitHub is not a penalty for a UI/UX target.
- The score is **diagnostic, not predictive**: no published study yet shows proof-of-work scores predict placement outcomes. A pilot against VIT placement data would be the natural next step.

---

## 9. Key sources

- Competitors: [Simplify Copilot](https://simplify.jobs/copilot), [Teal pricing](https://www.tealhq.com/pricing), [Huntr pricing](https://huntr.co/pricing), [Careerflow FAQ](https://www.careerflow.ai/faq), [Rezi pricing](https://www.rezi.ai/pricing)
- Prior art: [HackerRank hiring-agent](https://github.com/interviewstreet/hiring-agent), [GradPipe](https://www.everydev.ai/tools/gradpipe), [Devpost Verify](https://devpost.com/software/verify-27gui6), [RashDev](https://fossunited.org/hack/fosshack26/p/fckh0ajbou), [LinkedIn verified skills](https://techcrunch.com/2026/01/28/linkedin-will-let-you-show-off-your-vibe-coding-chops-with-a-certificate/)
- India: [Superset for universities](https://joinsuperset.com/university.html), [PlacementPreparation.io for colleges](https://www.placementpreparation.io/for-colleges/), [India Skills Report 2026](https://news.careers360.com/india-skills-report-2026-employability-56-35-pc-ai-tools-digital-gig-economy-workforce-global-talent-hub)
- Signals: [OpenSSF Scorecard](https://github.com/ossf/scorecard), [UW–Madison repo quality](https://ospo.wisc.edu/blog/2024/repo-quality-metrics), [commit consistency (arXiv 2508.02487)](https://arxiv.org/html/2508.02487v2), [Dolos](https://arxiv.org/html/2402.10853v2), [AI-resume detection (LREC 2026)](https://preview.aclanthology.org/ingest-lrec/2026.lrec-main.581/)
- Stack: [Gemini changelog](https://ai.google.dev/gemini-api/docs/changelog), [Gemini terms](https://ai.google.dev/gemini-api/terms), [Groq limits](https://console.groq.com/docs/rate-limits), [Vercel limits](https://vercel.com/docs/limits), [Supabase pricing](https://supabase.com/pricing), [Render free](https://render.com/docs/free), [GitHub GraphQL limits](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api), [LinkedIn API access](https://learn.microsoft.com/en-us/linkedin/shared/authentication/getting-access)
- Agents: [Claude Code memory](https://code.claude.com/docs/en/memory), [permissions](https://code.claude.com/docs/en/permissions), [worktrees](https://code.claude.com/docs/en/worktrees), [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Codex pricing](https://learn.chatgpt.com/docs/pricing), [Prism](https://github.com/stoplightio/prism), [openapi-typescript](https://openapi-ts.dev/introduction)

Full research report with all sources: `docs/RESEARCH.md`.
