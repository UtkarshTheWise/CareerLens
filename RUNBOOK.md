# CareerLens — execution runbook (two laptops)

The short version of who does what, in order. Details and copy-paste prompts live in `PROMPTS.md`; the schedule and task list in `ROADMAP.md`.

| | **Backend lead** (Claude Code) | **Frontend lead** (Codex) |
|---|---|---|
| Laptop | Backend lead's | Frontend lead's |
| Owns | `apps/api/`, `data/`, the contract, Phase 3 integration | `apps/web/`, `apps/extension/`, root package files |
| Branch | `backend/claude` (and `integration` in Phase 3) | `frontend/codex` |
| Talks to | real APIs (Gemini, Groq, GitHub, Supabase) | local mock API only until Phase 3, so no API keys needed |
| Progress file | `docs/progress/backend.md` | `docs/progress/frontend.md` |
| Handoff log (append only) | `docs/handoff/backend.md` | `docs/handoff/frontend.md` |

## Golden rules (both)

1. **GitHub is the only link between laptops.** No zips or pen drives. Push after every commit, including `wip` commits.
2. **The contract (`contracts/openapi.yaml`) is frozen.** Changes go through a Contract Change Request in your handoff log; the backend lead approves and edits it on `main`.
3. **Never edit the other side's folders.** Need something? Write it in your handoff log.
4. **One task = one fresh agent session**: read progress file → paste task prompt + progress footer → approve the plan → let it build → check its summary and checks → commit + push.
5. **Progress file is updated after every step.** If an agent hits a limit, any other model continues from it.
6. **Never share or commit API keys.** The frontend lead doesn't need any.

---

## Step 0 — Before the event

**Both**
- [ ] Check DataQuest's rules on pre-written code. If code written before the event isn't allowed, do only Step 0 and the Phase 0 contract review in advance.
- [ ] Read `README.md` sections 1–3 and skim `docs/QUIZ.md`, so you can both pitch it.
- [ ] Agree on the hackathon timeline and when you'll do the checkpoint calls (H6, H12, H14).

**Backend lead**
- [ ] Create a **personal** GitHub repo (not an org; Vercel's free plan can't deploy org repos), push the kit, add the frontend lead as a collaborator.
- [ ] Accounts and keys: Google AI Studio (owned by someone 18+), Groq, GitHub fine-grained token (public repos, read only), Supabase, Render, Vercel.
- [ ] In AI Studio, note the exact Gemini model IDs and free quota; put them in `apps/api/.env` later.
- [ ] Install: git, Python 3.12 + `uv`, Node 20+ + `pnpm`, Claude Code. Optional insurance: Ollama with a small model pulled.

**Frontend lead**
- [ ] Accept the GitHub invite.
- [ ] Install: git, Node 20+ + `pnpm`, Codex CLI, Chrome.
- [ ] Confirm Codex access (CLI needs ChatGPT Plus or an API key) and check the model with `/model`. **If you don't have access, tell the backend lead now**: the frontend track can run on Claude Code or another model using the same prompts.
- [ ] Look through `docs/DESIGN.md` and `design-refs/`; add any other reference images there.

---

## Step 1 — Phase 0: freeze the contract (H0 → H2)

**Backend lead**
```bash
git clone <repo> careerlens && cd careerlens
claude --permission-mode plan        # then paste prompt P0 from PROMPTS.md
```
- [ ] Claude Code proposes contract changes → **review them together** (frontend lead checks the UI has every field it needs).
- [ ] Approve → it adds example data, creates root package files and the generated API client, fills the progress files' environment sections.
- [ ] `git tag v0.2.0 && git push origin main --tags`
- [ ] Tell the frontend lead "P0 is pushed".

**Frontend lead** (meanwhile): review the contract proposal with the backend lead; prepare the DESIGN tokens questions.

---

## Step 2 — Set up both laptops (≈ 15 min)

**Backend lead**
```bash
cd careerlens
git worktree add ../careerlens-api -b backend/claude
cp .claude/backend.settings.local.json ../careerlens-api/.claude/settings.local.json
cp apps/api/.env.example ../careerlens-api/apps/api/.env      # fill in keys
cd ../careerlens-api && git push -u origin backend/claude
claude                                                        # start B1
```

**Frontend lead**
```bash
git clone <repo> careerlens-web && cd careerlens-web
git checkout -b frontend/codex && git push -u origin frontend/codex
pnpm install                                                   # normal terminal, not inside Codex
npx @stoplight/prism-cli mock contracts/openapi.yaml -p 4010 -d   # leave running
codex                                                          # start F1
```
Codex's sandbox has no network by default, so keep installs and the mock server in your own terminals.

---

## Step 3 — Build in parallel (H2 → H14)

| Order | Backend lead (Claude Code) | Frontend lead (Codex) |
|---|---|---|
| 1 | B1 Scaffold | F1 Scaffold + design tokens + API client |
| 2 | B2 Skill/role/resource catalogues | F2 Component kit |
| 3 | B3 Ingest + LLM gateway + resume extraction | F3 Onboarding + analysis progress |
| — | **H6 checkpoint** | **H6 checkpoint** (F1–F3 should be done by ~H8) |
| 4 | B4 GitHub collector + detectors | F4 Dashboard + evidence report + what-if |
| 5 | B5 Scoring engine | F9 Project quiz screens |
| 6 | B6 Pipeline + analyses + roadmap | F5 Roadmap + history |
| 7 | B7 Jobs, applications, cohorts, seed data | F6 Placement-cell page |
| — | **H12 checkpoint** | **H12 checkpoint** |
| 8 | B9 Project quiz backend | F7 Tracker Kanban |
| 9 | B8 Hardening + deploy | F8 Chrome extension |
| — | **H14 checkpoint** | **H14 checkpoint** |

**Each task, both of you:**
1. New session (`/clear` in Claude Code; new session in Codex).
2. Paste the task's prompt from `PROMPTS.md`, with the prefix line for your phase and the **progress footer** at the end.
3. Read its plan; approve or correct.
4. When it finishes: check its summary matches the checks it ran, then make sure it committed and pushed.

**Frontend lead:** the frontend estimates add up to ~16 h for 12 h. After F2, run a second Codex session in parallel for the extension (F8) in the same clone; it only touches `apps/extension/`.

---

## Step 4 — Checkpoints (H6, H12, H14): 10 minutes, both

1. Each opens a pull request into `main` on GitHub (`backend/claude → main`, `frontend/codex → main`).
2. Backend lead merges both.
3. Both: `git pull --rebase origin main`; frontend lead also runs `pnpm gen:client` if the contract changed.
4. Read each other's progress file:
   `git fetch && git show origin/frontend/codex:docs/progress/frontend.md` (or `backend/claude:docs/progress/backend.md`).
5. Five-minute call: what's done, what's behind, anything to cut (use the P0/P1/P2 list in `ROADMAP.md`).

---

## When something goes wrong

| Problem | What to do |
|---|---|
| Agent hits its usage or context limit | Paste **CHECKPOINT** (if it still responds) → push → open another model in the same folder → paste **RESUME** (both in `PROMPTS.md`). |
| Frontend needs a field the API doesn't have | Frontend lead writes a CCR in `docs/handoff/frontend.md` and pushes → backend lead approves, edits the contract on `main`, pushes → both pull. Keep building against the current contract meanwhile. |
| Agent edited the other side's files | Paste the "Agent touched files it doesn't own" recovery prompt. |
| Gemini quota runs out | Paste the "LLM quota exhausted" recovery prompt; Groq takes over. |
| Codex unusable for the rest of the event | Frontend lead runs CHECKPOINT + push; either continue with another model on the same laptop, or the backend lead takes the branch (see "Two-laptop setup" in `PROMPTS.md`). Agree who owns the branch from then on. |
| Laptop dies | Everything pushed is safe; clone again on any laptop and RESUME. |

---

## Step 5 — Phase 3: integration (H14 → H18), backend lead's laptop

**Backend lead**
```bash
cd careerlens && git fetch
git checkout -b integration origin/main
git merge origin/backend/claude origin/frontend/codex
claude --permission-mode plan          # I1, then I2, I3, I4 from PROMPTS.md
```
- [ ] Push `integration` after each task.

**Frontend lead**
- [ ] Pull `integration`, run the web app against the backend lead's backend (same Wi-Fi with `--host 0.0.0.0`, or the Render URL).
- [ ] Load the extension and test it on a real Greenhouse, Lever and LinkedIn job page.
- [ ] Click through every screen in light and dark mode; log bugs in `docs/handoff/frontend.md` (or tell the backend lead directly).
- [ ] Fix pure UI bugs on a short branch off `integration` if the backend lead agrees.

---

## Step 6 — Phase 4: demo hardening (H18 → H24)

**Backend lead**
- [ ] Seed the 40-student demo batch; run both demo personas' analyses and pre-generate their quizzes so the demo is served from cache.
- [ ] Test with Wi-Fi off using Ollama.
- [ ] Deploy (Render + Vercel) as a backup to the local demo.

**Frontend lead**
- [ ] Final UI polish, both themes, phone width.
- [ ] Install the extension on the demo laptop.
- [ ] Record the 2-minute backup video.

**Both**
- [ ] Pitch: problem stats → prior art (be upfront about HackerRank's hiring-agent and GradPipe) → five differentiators → live demo → what's next.
- [ ] Rehearse the demo path twice: persona 1 (strong GitHub, inflated skills) → report → what-if → **live verify quiz** showing a skill move from `moderate` to `strong` → placement-cell view → extension on a job page. Persona 2 (designer, no GitHub) shows fairness.

## T-15 minutes before judging

- [ ] Backend running locally and `/health` OK; hit the Render URL to wake it.
- [ ] Open the Supabase dashboard (wakes a paused project).
- [ ] Demo browser tabs open: dashboard, report, quiz, placement page, one job page.
- [ ] Backup video on both laptops.
