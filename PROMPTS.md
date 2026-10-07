# PROMPTS.md — Claude Code ↔ Codex playbook

Copy-paste prompts for every task in `ROADMAP.md`. Task ids match.

## How the coordination works

```
                 contracts/openapi.yaml  (frozen, human-owned)
                    │                 │
     pnpm gen:client│                 │FastAPI must emit the same shapes
                    ▼                 ▼
 packages/api-client (generated)    apps/api  ◄── Claude Code, worktree backend/claude
          ▲                                     .claude/settings.local.json blocks web/extension edits
          │ imports
 apps/web + apps/extension  ◄── Codex, worktree frontend/codex, talks to Prism mock :4010
          │
          └── docs/HANDOFF.md (append-only): status, requests, Contract Change Requests
                                   │
                Phase 3: Claude Code on branch `integration` merges both, points web at :8000,
                runs drift check + builds + smoke tests, fixes mismatches.
```

Rules that make this work:
1. **Shared instructions live in `AGENTS.md`.** Codex reads only AGENTS.md files; Claude Code reads `CLAUDE.md`, which imports AGENTS.md. Never put shared rules only in CLAUDE.md.
2. **One task per session.** Start a fresh session (`/clear` in Claude Code, new `codex` session) for each task id. Paste the prompt. Context stays small; quality stays high.
3. **Plan before edit** for anything bigger than a small fix (Claude Code: `Shift+Tab` into plan mode or `claude --permission-mode plan`; Codex: ask it to "propose a plan and wait").
4. **Every task ends** with: checks run → progress file updated → HANDOFF entry (if the other track needs to know) → commit.
5. **Humans merge.** Merge `backend/claude` and `frontend/codex` into `main` at checkpoints; the other side rebases.
6. **Progress files make agents swappable.** Each track keeps `docs/progress/<track>.md` current after every step (rules in `AGENTS.md`). If an agent hits its usage or context limit, any other model (Claude Code, Codex, Gemini CLI, Cursor…) picks up the same track with the **RESUME** prompt below. Claude Code is forced to do this by a Stop hook; Codex and other tools rely on the footer below.

### One-time setup

```bash
git clone <your personal repo> careerlens && cd careerlens   # main checkout: Phase 0, merges, Phase 3
# ... run P0 here, commit to main ...
git worktree add ../careerlens-api -b backend/claude          # Claude Code works here (Phase 1)
cp .claude/backend.settings.local.json ../careerlens-api/.claude/settings.local.json   # ownership guardrail
git worktree add ../careerlens-web -b frontend/codex          # Codex works here (Phase 2)
cp apps/api/.env.example ../careerlens-api/apps/api/.env      # fill keys; never commit
```

Terminals: (1) `claude` in `careerlens-api/`, (2) `codex` in `careerlens-web/`, (3) Prism mock from either, (4) dev servers. Phase 3 runs `claude` back in `careerlens/`.

**Codex sandbox note:** Codex's default sandbox has network off, so it can't `pnpm install` or reach the mock. Either run installs and dev servers yourself in terminal 3/4 (simplest), or allow network for its workspace sandbox in `~/.codex/config.toml` (check the current Codex docs for the exact key).

---

## Phase 0 — Contract freeze (Claude Code, plan mode)

### P0

```
Phase 0. Read README.md, docs/SCORING.md, docs/PIPELINE.md, docs/DESIGN.md and contracts/openapi.yaml.

1. Review the contract against SCORING.md and PIPELINE.md. List every field the UI in DESIGN.md
   would need that is missing, every field nothing produces, and any naming inconsistency.
   Propose changes as a YAML diff. Do not apply yet.
2. After I approve: apply the changes, add realistic `examples` to AnalysisReport, ScoreBreakdown,
   SkillClaim, ProjectAudit, RoadmapMilestone, JobMatch and CohortInsights so the Prism mock
   returns believable data for a CSE student targeting sde-backend. Validate the spec.
3. Create root package.json + pnpm-workspace.yaml (workspaces: apps/web, apps/extension,
   packages/*) with script "gen:client": "openapi-typescript contracts/openapi.yaml -o packages/api-client/schema.d.ts",
   create packages/api-client (package.json, index.ts exporting `paths`, `components` types and a
   `createApiClient(baseUrl, token = "dev")` built on openapi-fetch that always sends
   `Authorization: Bearer <token>`). Only schema.d.ts is generated; the wrapper is hand-written once here. Run it.
4. Create apps/api/.env.example from README section 7.
5. Verify `npx @stoplight/prism-cli mock contracts/openapi.yaml -d` starts and serves /v1/roles
   (send `Authorization: Bearer dev`; Prism enforces the security scheme).
6. Record the freeze under *Decisions* in docs/progress/integration.md, fill the *Environment* sections of
   docs/progress/backend.md and frontend.md with what you set up, append a HANDOFF entry and commit to
   main as "chore(contract): freeze v0.2.0".
```

Human: approve, tag `v0.2.0`, then tell Codex the root package files are now its own.

---

## Phase 1 — Backend (Claude Code, branch `backend/claude`)

Prefix each prompt with: `Phase 1, task <id>. Read docs/progress/backend.md first. Plan first, wait for my OK, then implement.`
End each prompt with the **progress footer** (see "Switching models" below).

### B1 — Scaffold

```
Scaffold apps/api per apps/api/AGENTS.md using uv (Python 3.12): FastAPI app factory, pydantic-settings
config, SQLAlchemy 2 models (profiles, documents, analyses, applications, cohorts, cache) with Alembic
or create_all for the prototype, DEV_AUTH dependency, global exception handler returning the contract
Error shape, CORS (CORS_ORIGINS + allow_origin_regex for chrome-extension://).
Implement GET /health, GET /v1/roles (from data/roles.yaml; create a 1-role placeholder if B2 not done),
GET /v1/me (demo profile when DEV_AUTH=1).
Write scripts/check_contract.py: load contracts/openapi.yaml and app.openapi(); report missing/extra
paths+methods, and for each response schema compare property names, required lists and enums.
Exit 1 on mismatch; support --only-implemented to ignore paths not yet routed.
Pydantic models in app/schemas/api.py must mirror the contract names exactly.
Tests: health, roles, me, error shape. Run pytest, ruff, check_contract --only-implemented.
```

### B2 — Catalogues

```
Create data/skills.yaml (~60 skills covering the 7 roles in apps/api/AGENTS.md, with aliases and
detectors in the format of docs/SCORING.md §4), data/roles.yaml (7 roles; each 8–14 skills with
importance 1–3 and per-role component weights; ui-ux-designer uses the designer weights),
data/resources.yaml (≥2 per skill; ONLY real, well-known free resources whose URLs you are confident
exist — official docs, freeCodeCamp, MDN, roadmap.sh, CS50, Kaggle Learn, Google UX on Coursera audit,
etc.; mark each with type and hours), data/tutorial_names.txt, data/readme_templates.txt
(first lines of CRA / Next.js / Vite / Django / Spring starters).
Add app/catalogue.py loaders with validation and tests: every role skill exists, every skill has
≥2 resources, aliases are unique across skills.
```

### B3 — Ingest, LLM gateway, resume extraction

```
Implement services/ingest.py (pdfplumber for PDF, python-docx for DOCX, 5 MB limit, page count,
PII stripper for emails/phones/URLs-with-usernames/header name line — return stripped text plus a
local map), POST /v1/profiles, GET/PATCH /v1/profiles/{id}, POST /v1/profiles/{id}/documents.
Implement services/llm.py generate_structured(schema, system, user, tier) exactly as described in
docs/PIPELINE.md "Design rules": Gemini (google-genai, response JSON schema from Pydantic,
models from GEMINI_MODEL_FAST/SMART, no temperature) → on 429/5xx/timeout Groq (json_schema strict,
GROQ_MODEL) → Ollama if OLLAMA_URL. Cache in the cache table by sha256. Validate with Pydantic; one
retry with the validation error appended. Log provider + latency, never content.
Add prompts/extract_resume.md and schemas/llm.py ResumeProfile from PIPELINE.md stage 2.
Tests (offline): ingest on a fixture PDF you generate in tests/fixtures, PII stripping, gateway
fallback with mocked 429, cache hit, validation retry.
```

### B4 — GitHub collector and detectors

```
Implement services/github.py: the GraphQL overview query from docs/PIPELINE.md stage 3 with
GITHUB_TOKEN, then recursive trees for the top 8 non-fork repos, authored-commit counts per repo,
202 retry with backoff, 24h cache, graceful handling of unknown user / rate limit (Error codes
github_not_found, rate_limited).
Implement services/detectors.py: run skills.yaml detectors over each repo (manifests, files, paths,
extensions, limited content/import regex), compute repo signals used by SCORING.md §2B
(readme length + template match, licence, homepage, tests, CI, lockfile, structure, deploy config,
authored share, fork status, commits, active span, code size) and the rule flags in SCORING.md §5
(single_dump, unmodified_fork, default_readme, tutorial_pattern, thin_wrapper). claim_mismatch and
vague_description are completed in B6.
Record one real public GitHub profile's responses into tests/fixtures/github/ with a small script
(scripts/record_github.py), then write offline tests against them.
```

### B5 — Scoring engine

```
Implement services/scoring.py as pure functions exactly per docs/SCORING.md: evidence levels and
credits, Evidence Coverage, components A–E, role weights from roles.yaml, reweighting when data is
missing, confidence + low-confidence cap at 60, design-item cap at 80, bands, reasons[] with
deltas and evidence_ids, role-fit (score the student against every role, return top 3 with reasons
and top_missing), gaps with estimated_gain, and simulate(signals, changes) for the what-if endpoint.
No I/O, no LLM. Write ≥25 unit tests including: same input → same output; no GitHub → reweighted +
confidence low + capped; designer without GitHub not penalised; the first two flags each lower the
authorship sub-score by 5 and it never goes below 0; simulate adding tests+CI increases project_quality.
```

### B6 — Pipeline and analysis endpoints

```
Implement services/pipeline.py running stages 1–8 from docs/PIPELINE.md as a BackgroundTask,
writing status + progress after each stage; POST /v1/profiles/{id}/analyses (202),
GET /v1/analyses/{id}, GET /v1/profiles/{id}/analyses, POST /v1/analyses/{id}/simulate.
Stage 5: prompts/judge_project.md (+ judge_design.md for portfolio URLs: fetch page with httpx,
extract title/OG/meta + visible text ≤3000 chars) → set vague_description and claim_mismatch flags
(claim_mismatch only when LLM unsupported_claims AND detectors agree).
Stage 7: prompts/plan_roadmap.md via services/planner.py; drop unknown ids; attach resources;
estimated_gain from scoring.simulate.
Build the full AnalysisReport exactly as the contract. Failures in one project's judging must not
fail the analysis (add a note instead).
Test end-to-end offline with fixtures + recorded LLM responses. Then run one live analysis on the
demo profile and paste the report summary into HANDOFF.
```

### B7 — Jobs, applications, cohorts, seed

```
Implement services/matching.py + POST /v1/jobs/match (if posting.source=="llm" or required_skills
empty, call prompts/extract_job.md first; normalise skills via aliases; keyword_match and
evidence_match per docs/PIPELINE.md; summary sentence). Applications CRUD. Cohorts: list, insights,
students, CSV export per SCORING.md §7 (must work on SQLite and Postgres).
scripts/seed_demo.py: demo profile + cohort "B.Tech CSE 2027" with 40 synthetic students whose stored
analyses are produced by running scoring.py over generated signal sets (no LLM calls), with
realistic spread: ~30% not ready, ~45% developing, ~25% ready, and a visible pattern (e.g. many claim
Docker/Kubernetes with weak evidence). Tests for insights maths.
```

### B9 — Project Understanding Check (quiz)

```
Phase 1, task B9. Implement docs/QUIZ.md end to end.
1. services/quiz_context.py: pick ≤5 key files for a project per QUIZ.md §2 (entry points, detector
   hits on claimed skills, largest authored source; skip generated/lock/vendor files), fetch via the
   GraphQL blob pattern, cap 6k chars each / 20k total, keep line numbers. Cache 24h.
   Design projects: case-study page text + description instead.
2. services/quiz.py: generate (prompts/quiz_generate.md, tier smart, GeneratedQuiz schema from
   docs/PIPELINE.md), validate source_refs against fetched files and MCQ correctness, request
   replacements once, cut code_snippet from cited lines, store answer keys server-side only
   (quiz_questions table). Verify = 6 questions with the QUIZ.md mix and time limits; practice ≤10
   with hints. Seed generation with attempt number so retakes get fresh questions.
3. Endpoints from the contract: POST /v1/analyses/{id}/quizzes, GET /v1/quizzes/{id} (verify: return
   answered questions + the current one only, record served_at), POST /v1/quizzes/{id}/answers
   (verify: record only, enforce order and server-side time limit + 10s grace; practice: grade now
   with tier fast and return feedback + model answer + source_ref), POST /v1/quizzes/{id}/submit
   (grade all remaining short answers in ONE call via prompts/quiz_grade.md; compute scores in
   Python per QUIZ.md §3; set project understanding; apply SCORING.md §6 by re-running scoring on the
   latest analysis; return SimulationResult as score_update; raise/clear understanding_gap flag),
   GET /v1/profiles/{id}/quizzes. Verify cooldown 1h starts at createQuiz → 429 with details.retry_at;
   one in-progress verify quiz per project; auto-submit expired verify quizzes on next access.
   Store understanding per project on the profile (keyed by repo/portfolio URL) so later analyses
   carry it forward.
4. Never return answer keys before grading. Never store focus data anywhere the cohort endpoints read.
5. Cohort insights: understanding summary + built_and_explained_rate per skill. Seed script: give
   ~60% of synthetic students a verify result with a realistic spread.
6. Tests (offline, recorded LLM fixtures): source_ref validation drops invented files; timed-out
   answer scores 0; key-point → score maths; demonstrated upgrades moderate→strong for covered skills
   only; not_demonstrated downgrades only covered skills whose sole evidence is that project; not_taken
   changes nothing; practice never changes evidence; design effects are symmetric and never exceed
   moderate; understanding survives a re-analysis; verify feedback has no key fields before submit; answer keys absent from GET responses.
Run check_contract.py, pytest, ruff. HANDOFF entry with one example generated quiz (questions only).
```

### B8 — Hardening and deploy

```
Make check_contract.py pass with no flags. Add request-size limit, timeouts on all external calls,
structured logging, /health reporting active LLM provider. Write apps/api/README.md (run, test,
seed, record fixtures). Add render.yaml for a free web service and .github/workflows/keepalive.yml
(daily curl to /health and a trivial Supabase query). Do not deploy secrets. Final HANDOFF entry
listing every endpoint's status (real / partial / stub).
```

---

## Phase 2 — Frontend (Codex, worktree `../careerlens-web`, branch `frontend/codex`)

End each prompt with the **progress footer** (see "Switching models" below).

Prefix each prompt with: `Task <id>. Read docs/progress/frontend.md, AGENTS.md, apps/web/AGENTS.md (or apps/extension/AGENTS.md) and docs/DESIGN.md first. Propose a short plan, then implement. Use only packages/api-client for API types. API base: http://localhost:4010 (Prism mock).`

### F1 — Scaffold and shell

```
Create apps/web: Next.js App Router + TypeScript strict, Tailwind, shadcn/ui, lucide-react, Recharts,
Framer Motion, next-themes, TanStack Query, Plus Jakarta Sans. Implement the tokens from
docs/DESIGN.md as CSS variables for light and dark, exposed to Tailwind v4 via `@theme` in globals.css;
next-themes with attribute="data-theme". App shell: left sidebar
(Dashboard, Report, Roadmap, Tracker, Placement cell, Settings) with active indicator, top bar with
theme toggle and profile chip. lib/api/client.ts using createApiClient(NEXT_PUBLIC_API_URL) and
Query hooks for every contract operation (typed from packages/api-client). Render /v1/roles on a
temporary page to prove the wiring. Add pnpm scripts dev/build/lint/typecheck.
```

### F2 — Component kit

```
Build the components in docs/DESIGN.md table: KpiCard, ScoreRing (animated stroke-dasharray, band
colours, centred value+label), SegmentedGauge, TrendCard (monotone lines, highlighted point,
tooltip bubble, Weekly/Monthly/Yearly tabs), StackedBars, LevelPill, BandBadge, EvidenceRow, FlagCard,
MilestoneCard, StageProgress, WhyPopover (renders ScoreComponent.reasons with +/- deltas).
Create /dev/components showing every component with mock data in both themes. Match the reference
style: 20px radius cards, soft shadows, icon chips, generous spacing.
```

### F3 — Onboarding and progress

```
/onboarding: 3-step wizard (1 name + upload resume PDF/DOCX + optional LinkedIn PDF or pasted text;
2 GitHub username + portfolio URLs; 3 target role from /v1/roles) → createProfile, uploadDocument,
startAnalysis → route to /report/[analysisId] which polls getAnalysis every 2s and shows
StageProgress until done/failed. Validation, error states, file size check (5 MB).
```

### F4 — Dashboard and evidence report

```
/dashboard: KPI row (Readiness ScoreRing, Evidence Coverage ring, verified skills count, top role
fit), "Why this score" SegmentedGauge with WhyPopover per component, Consistency TrendCard from
report.consistency, top 3 gaps, next roadmap milestone.
/report/[analysisId] (done state): claims table with level filter and evidence links; projects grid
with subscores, flags (FlagCard), what_it_does and honest_rewrite; role fits; notes (data gaps,
caps). Each project card shows an UnderstandingBadge and two buttons, "Practice" and "Verify my understanding" (createQuiz → /quiz/[quizId]). What-if panel: toggles per project (tests, CI, demo URL, licence, README) → simulateAnalysis
→ animate the score delta. Do not compute scores client-side.
```

### F9 — Project quiz

```
Build /quiz/[quizId] per docs/QUIZ.md §7 and docs/DESIGN.md (QuizCard, UnderstandingBadge):
intro screen (mode, question count, time per question, "graded on understanding, not English",
practice vs verify explained) → one question per screen using getQuiz; code_snippet rendered with
line numbers and syntax highlighting (shiki or prism-react-renderer); MCQ as large option cards;
short answer textarea (max 2000 chars). Verify mode: countdown ring from time_limit_s, auto-submit
the answer at 0, no back navigation, paste disabled (onPaste preventDefault + small notice), count
window blur/visibilitychange per question and send focus_lost_count. Practice mode: hint toggle,
then after answerQuizQuestion show key points (covered/partial/missing), feedback, model answer and
"view lines" link (source_ref.url). After the last question call submitQuiz and show the result:
quiz ScoreRing, UnderstandingBadge, score_update before→after with animated delta, per-question
review, review_topics with links, retake_available_at countdown. Add a quiz history list on the
report page (listQuizzes). Copy must never imply the student didn't build the project.
```

### F5 — Roadmap and history

```
/roadmap: ordered MilestoneCards with resources (external links), effort, +gain; local "done" toggle;
progress bar. Score history line chart from listAnalyses. Empty state prompting a re-scan.
```

### F6 — Placement cell

```
/placement: cohort select (listCohorts) + role select; KPI row (students, analysed, median readiness,
at-risk, median coverage); band distribution StackedBars; score histogram; top missing skills
horizontal bars; unverified-claim rate table (skill, claimed by, % unverified, sorted desc); understanding summary
(quizzed / demonstrated / partial / not demonstrated) and built-and-explained rate per skill; students
DataTable (name, dept, score ring mini, band, coverage, top gap, UnderstandingBadge, at-risk badge) with at-risk filter
and search; Export CSV button (exportCohort). This page must look excellent in both themes — it is a
demo highlight.
```

### F7 — Tracker

```
/tracker: Kanban with columns saved/applied/interviewing/offer/rejected; cards show company, title,
two mini rings (keyword vs evidence match), deadline. Drag to change status → updateApplication with
optimistic update. Add-manually dialog → createApplication.
```

### F8 — Chrome extension

```
Create apps/extension per apps/extension/AGENTS.md: MV3 manifest (action, side_panel, activeTab,
scripting, storage; no broad host permissions), Vite + React + Tailwind with the same tokens.
Side panel tabs: Match / Gaps / Save. "Analyse this job" injects an extractor: JSON-LD JobPosting
(including @graph) → site adapters (linkedin, greenhouse, lever, workday, naukri, generic) → visible
text fallback (source "llm"). Call matchJob; show Keyword vs Evidence-backed rings, matched with
LevelPills, missing, unverified, summary. Save → createApplication. Options page: API base URL,
profile id (button to fetch from getMe), theme. Write src/adapters/__tests__ with saved HTML
snippets for JSON-LD and Greenhouse.
```

---

## Phase 3 — Integration (Claude Code, branch `integration`)

Run Claude Code in the main checkout (`careerlens/`), which has no `.claude/settings.local.json`, so the phase-1 deny rules don't apply. Start with `/clear`.

### I1 — Integration plan (plan mode)

```
Phase 3, task I1. You are now the integrator, not a feature builder. Fill in
docs/progress/integration.md as you go. Read docs/progress/backend.md, docs/progress/frontend.md
and docs/HANDOFF.md fully,
then `git log main..backend/claude` and `git log main..frontend/codex` and their diffs (use a
subagent to summarise each side). Produce: (a) open CCRs and requests from each side, (b) every
place the frontend uses a field/endpoint the backend doesn't implement or implements differently,
(c) files changed outside each agent's ownership, (d) merge order and conflict hotspots
(lockfiles, root configs), (e) a step-by-step plan for I2–I3. Do not edit anything.
```

### I2 — Merge and wire

```
Phase 3, task I2. Execute the approved plan: create branch integration from main, merge
backend/claude then frontend/codex, resolve conflicts (root package files: keep Codex's; apps/api:
keep Claude's). Run pnpm gen:client and check_contract.py. Fix mismatches — prefer changing the
backend to match the contract; change frontend only for genuine frontend bugs, minimal diffs, no
redesigns. Set apps/web/.env.local NEXT_PUBLIC_API_URL=http://localhost:8000 and the extension
default. Run: backend pytest + ruff + check_contract, web lint + typecheck + build, extension build.
Report each result.
```

### I3 — End-to-end smoke

```
Phase 3, task I3. Write scripts/smoke_e2e.py that, against a running local stack, seeds demo data,
creates a profile from tests/fixtures resume, starts an analysis, polls to done, calls simulate,
runs a practice quiz and a verify quiz with recorded answers (asserting the score changes and answer
keys never leak before grading),
lists analyses, matches a fixture JobPosting, creates and moves an application, and fetches cohort
insights + CSV — asserting contract shapes. Run it and fix failures. Then write
docs/DEMO_CHECKLIST.md for the manual UI path (onboarding → report → what-if → roadmap → tracker →
placement → practice and verify quiz → extension on a Greenhouse, a Lever and a LinkedIn job page) and walk through what you
can verify from the CLI.
```

### I4 — Independent review

```
Phase 3, task I4. Spawn a fresh subagent with no prior context. Give it README.md, the DQWL problem
statement requirements (evidence-based analysis; explainable scoring; multi-source evaluation;
skill gaps; roadmap; role-fit; batch-level insights for placement teams), and the repo. Ask it to
report ONLY: correctness bugs, unmet requirements, security issues (keys, CORS, PII reaching the
LLM, secrets in git, quiz answer keys reachable before grading, focus data reaching cohort
endpoints), and places that call students' work "slop/fake", imply a low quiz result means they
didn't build the project, or claim AI-text detection.
No style nits. Then fix what it finds and append a final HANDOFF entry.
```

---

## Switching models (progress files)

### Progress footer — append to EVERY task prompt, for every agent

```
Progress rules (AGENTS.md "Progress file"): keep docs/progress/<backend|frontend|integration>.md current.
After each meaningful step, update Status, "Resume here", the Task board row and In-progress detail;
write your agent + model name in "Last updated". Commit code and progress file together (wip(...) if
unfinished). Before you say you're done, the task row must be "done" with its commit sha.
```

### CHECKPOINT — when a limit is close, before `/compact`, or before you close the laptop

```
CHECKPOINT. Stop feature work now.
1. Run the checks for your track and note pass/fail.
2. Rewrite docs/progress/<track>.md so a different AI model with zero context can continue:
   current task + state, an exact numbered "Resume here" (file, function, what's left, next command),
   files touched but unfinished, stubs (TODO(progress)), failing tests, decisions, gotchas.
3. Commit everything on your branch as `wip(<area>): checkpoint <task id>` (or a normal commit if done).
4. Reply with the "Resume here" section only.
```

### RESUME — paste into ANY agent/model taking over a track

```
You are taking over the <backend | frontend | integration> track of CareerLens from another AI agent
that stopped mid-task (usage or context limit). Don't start coding yet.
1. Read, in order: AGENTS.md, <apps/api/AGENTS.md | apps/web/AGENTS.md + apps/extension/AGENTS.md>,
   docs/progress/<track>.md (fully), the last 5 entries of docs/HANDOFF.md, and the PROMPTS.md
   prompt for the current task id.
2. Run `git status`, `git log --oneline -10` and the track's checks. If reality disagrees with the
   progress file, trust git and the checks, and correct the progress file first.
3. Reply in ≤10 lines: current task, what's done, what's half-done, what you'll do next, anything
   that looks broken. Then wait for my OK.
4. Continue from "Resume here" under the same ownership rules as the previous agent. Follow the
   progress footer rules and put your own agent + model name in "Last updated".
```

### Handing a track to a different tool

1. Make the outgoing agent run **CHECKPOINT** (if it still can). If it was cut off mid-step, run `git status` yourself; uncommitted work is still on disk in that worktree.
2. Open the new tool **in the same worktree** (`../careerlens-api` for backend, `../careerlens-web` for frontend) so it sees the same branch and files.
3. Ownership guardrails:
   - New agent is **Claude Code** on the frontend track → copy `.claude/frontend.settings.local.json` to `.claude/settings.local.json` in that worktree. On the backend track the backend file is already there.
   - New agent is **Codex** on the backend track → nothing to copy; `AGENTS.md` + `apps/api/AGENTS.md` carry the rules. Watch `git diff --stat` before merging.
   - **Any other tool** (Gemini CLI, Cursor, Aider…) → if it doesn't read `AGENTS.md` automatically, the RESUME prompt makes it read it explicitly.
4. Paste **RESUME**. Approve its summary only if it matches `git log`.

## Recovery prompts

**Contract drift found mid-build (either agent)**
```
Stop. Do not change contracts/openapi.yaml or the other side's code. Write a Contract Change Request
in docs/HANDOFF.md using the template, implement against the CURRENT contract with a TODO, and tell
me the CCR number.
```

**Agent touched files it doesn't own**
```
Run `git diff --stat main...HEAD`. Revert every change outside your ownership listed in AGENTS.md.
Move any needed change into a HANDOFF request instead.
```

**LLM quota exhausted**
```
Switch tier "smart" to the fast model for the rest of the session via env, confirm Groq fallback
works with a forced 429 test, and make sure all demo analyses are served from cache.
```

**Codex unavailable**
Copy `.claude/frontend.settings.local.json` to `../careerlens-web/.claude/settings.local.json` (denies `apps/api`, `data`, `contracts`), then run the F-prompts with Claude Code in that worktree. The ownership and contract rules don't change.
