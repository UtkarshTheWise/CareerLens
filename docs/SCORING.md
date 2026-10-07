# Scoring specification

The score must be **deterministic and explainable**. The LLM extracts facts and judges text; it never produces a number that goes into the score directly except through the rubric fields defined below. Same inputs → same score.

Every point awarded or withheld produces a `ScoreComponent.reasons[]` entry with a human sentence and, where possible, an `evidence_id` linking to a URL. That is what the "Why this score?" UI renders.

---

## 1. Evidence levels (per claimed or required skill)

| Level | Credit | Rule |
|---|---|---|
| `strong` | 1.00 | A detector (section 4) fires in at least one **non-fork** repo where the student authored **≥ 5 commits** and **≥ 40 %** of commits. |
| `moderate` | 0.70 | Detector fires but authorship is below the strong threshold; **or** a repo's primary language/topic matches; **or** a work-experience bullet names the skill with a concrete outcome; **or** a design portfolio item with a written case study (for design skills). |
| `weak` | 0.35 | Mentioned only in project descriptions, LinkedIn export text or a certificate, with no artifact. |
| `unverified` | 0.10 | Appears only in the skills list. |
| `missing` | 0.00 | Required by the target role, not claimed, no evidence. |

Skill names are normalised through `data/skills.yaml` aliases before matching (`ReactJS`, `React.js` → `react`).

**Evidence Coverage** (headline metric, replaces the draft's "integrity score"):
`coverage = 100 × (# claimed skills at strong or moderate) / (# claimed skills)`.

---

## 2. Job Readiness Score (per target role)

```
JRS = Σ  weight_c × component_c          (each component is 0–100)
```

| Component | Default weight | Designer roles |
|---|---|---|
| A. Skill evidence | 0.40 | 0.40 |
| B. Project quality | 0.25 | 0.30 (portfolio items) |
| C. Consistency | 0.15 | 0.05 |
| D. Experience | 0.10 | 0.15 |
| E. Resume quality | 0.10 | 0.10 |

Role-specific weights live in `data/roles.yaml` so they can be tuned without code changes.

### A. Skill evidence

For the role's required skills `s` with importance `w_s` (from `roles.yaml`, 1–3):

```
A = 100 × Σ w_s × credit(level_s) / Σ w_s
```

### B. Project quality

Pick the top 3 projects by relevance to the role (overlap between project's detected skills and the role's skills). `B` = mean of their project scores. Project score (0–100):

| Sub-score | Points | Signals |
|---|---|---|
| Hygiene | 20 | README > 300 chars and not a framework default (8) · repo description (3) · licence (3) · homepage/demo URL (4) · README has setup/usage section or screenshots (2) |
| Engineering | 30 | tests present (10) · CI workflow in `.github/workflows` (8) · dependency manifest + lockfile (4) · structured source tree, ≥ 2 modules (4) · deploy config (Dockerfile, vercel.json, Procfile…) (4) |
| Authorship & originality | 30 | authored-commit share, linear from 20 % (0) to 60 % (15) · not a fork, or fork with ≥ 5 own commits (5) · no low-evidence flags (10, −5 per flag, min 0) |
| Depth | 20 | authored commits, linear 0→30 (8) · active span, linear 0→4 weeks (6) · code size, linear 0→20 KB of non-generated code (6) |

**Design portfolio items** (link-based) use an LLM rubric instead (section 5 of `PIPELINE.md`): problem statement (25), process evidence such as research/wireframes/iterations (30), outcome or metrics (20), tool evidence matching claimed tools (15), presentation (10). Because this evidence can't be verified like code, design project scores are **capped at 80** and labelled "self-reported evidence".

### C. Consistency (from the GitHub contribution calendar, last 26 weeks)

```
active_ratio = active_weeks / 26                         → 50 %
stability    = 1 − min(CV_weekly_commits, 2) / 2         → 30 %   (CV = std/mean of weekly counts)
recency      = 1 if last activity ≤ 14 days, linear to 0 at 90 days → 20 %
C = 100 × (0.5·active_ratio + 0.3·stability + 0.2·recency)
```

### D. Experience

Internships, jobs, research roles or freelance work from the resume / LinkedIn export: 0 roles → 0, 1 → 60, 2+ → 100, then multiply by `0.6 + 0.4 × quantified_bullet_ratio`.

### E. Resume quality

Required sections parsed (contact, education, skills, projects, experience) 40 · quantified bullet ratio 30 · length 1–2 pages 15 · skills list not inflated (≤ 25 skills **and** < 50 % unverified) 15.

---

## 3. Missing data, confidence and bands

- Only two components can be "no data": **Consistency** (no GitHub linked) and **Project quality** (no repos and no portfolio items). Their weight is **redistributed proportionally** across the others, and the report states it. **Experience** and **Resume quality** are never reweighted: zero roles is real data and scores 0.
- `confidence`: `high` (GitHub + resume + one more source), `medium` (resume + one source), `low` (resume only). With `low` confidence the JRS is **capped at 60**, and the report says why.
- Missing GitHub is **not** penalised for designer roles; missing portfolio is.

| Band | Range | Label | Colour token |
|---|---|---|---|
| Not ready | 0–49 | "Not yet ready" | `--danger` |
| Developing | 50–74 | "Developing" | `--warning` |
| Ready | 75–100 | "Ready" | `--success` |

---

## 4. Skill detectors (`data/skills.yaml`)

Detectors are cheap, deterministic, and run on data GitHub already returns (file tree, manifests, languages). Example entries:

```yaml
- id: react
  name: React
  aliases: [react, reactjs, react.js]
  category: frontend
  detectors:
    npm: [react]

- id: docker
  name: Docker
  aliases: [docker, containerization, containers]
  detectors:
    files: [Dockerfile, docker-compose.yml, docker-compose.yaml, compose.yaml]

- id: kubernetes
  name: Kubernetes
  aliases: [k8s, kubernetes]
  detectors:
    files: [Chart.yaml, kustomization.yaml]
    paths: ["k8s/", "helm/", "manifests/"]
    content: { glob: "*.y*ml", regex: "kind:\\s*(Deployment|Service|Ingress|StatefulSet)" }

- id: pytorch
  name: PyTorch
  aliases: [pytorch, torch]
  detectors:
    pip: [torch]
    imports: { lang: python, modules: [torch] }

- id: sql
  name: SQL
  aliases: [sql, mysql, postgresql, postgres]
  detectors:
    extensions: [.sql]
    pip: [sqlalchemy, psycopg, psycopg2, pymysql]
    npm: [pg, mysql2, prisma, drizzle-orm]
```

Detector types: `npm` (package.json deps), `pip` (requirements*.txt / pyproject.toml), `maven`/`gradle`, `files` (exact filenames anywhere), `paths` (dir prefixes), `extensions`, `content` (regex over a small number of matching files, max 5 files per repo), `imports` (regex on first 200 lines of up to 10 source files). Seed ~60 skills covering the role catalogue.

---

## 5. Low-evidence project flags (replaces "AI-slop")

Flags describe **missing evidence**, never authorship of text. Each flag carries `severity`, `reason`, `fix`, and `estimated_gain` (recomputed score delta if fixed).

| Code | Rule | Example fix |
|---|---|---|
| `single_dump` | ≤ 3 authored commits, or the first commit adds ≥ 80 % of the code | "Commit in meaningful steps; add a CHANGELOG of what you built and when." |
| `unmodified_fork` | Fork with 0 authored commits after the fork date | "Remove it from the resume or add your own feature and link the diff." |
| `default_readme` | README matches a framework template (CRA, Next.js, Vite starters) and < 300 extra chars | "Write a README: problem, architecture diagram, setup, screenshots, results." |
| `tutorial_pattern` | Name/description matches a known tutorial list (todo, weather, netflix-clone, …) **and** Depth sub-score < 8/20 | "Extend beyond the tutorial: add auth, tests, a deployed demo, one original feature." |
| `thin_wrapper` | Depends on an LLM SDK, < ~300 non-generated lines, description claims "autonomous/agentic/AI system" | "Describe it accurately, or add evaluation, retrieval, tool use, and measured results." |
| `claim_mismatch` | Project description names a technology no detector finds in the repo | "Either remove the claim or link the code that uses it." |
| `vague_description` | LLM rubric: no metric, no architecture, buzzword-heavy (see `PIPELINE.md` stage 5) | "Add one number (latency, users, accuracy) and one sentence on how it works." |
| `understanding_gap` | Latest **verify** quiz on this project scored < 40 (`docs/QUIZ.md`) | "Review `<path>` lines a–b; retake the quiz in 1 hour." |

---

## 6. Project Understanding Check (quiz) effects

Full spec in `docs/QUIZ.md`. Each project carries `understanding` from its latest verify quiz:

| `understanding` | Effect (applied after §1 levels, before §2 components) |
|---|---|
| `not_taken` | None. Skipping is never penalised. |
| `demonstrated` (quiz ≥ 70) | Code: covered skills at `moderate` from this project → `strong`; authorship & originality +5 (cap 30). Design: covered skills at `weak` → `moderate`; design project score +5 (cap 80). |
| `partial` (≥ 40 and < 70) | No change. |
| `not_demonstrated` (< 40) | `understanding_gap` flag (−5 on authorship & originality, or on the design project score). Covered skills whose **only** evidence is this project drop one level. |

"Covered skills" = the quiz questions' `skill_ids`. `understanding` is stored per project on the profile and carried into later analyses. Practice quizzes never affect the score.

Submitting a verify quiz re-runs this stage and §2 only (pure function) and stores the new breakdown on the analysis.

## 7. What-if simulator

`POST /v1/analyses/{id}/simulate` takes hypothetical signal changes (e.g. `{ "changes": [{ "project_id": "...", "add_signals": ["tests", "ci", "demo_url"] }] }`) and returns the recomputed JRS and delta. Pure function over stored signals, no LLM, no GitHub call. This is also how `estimated_gain` on roadmap items and flags is computed (for `understanding_gap`, simulate with `set_understanding: demonstrated`).

---

## 8. Cohort metrics (placement cell)

For a cohort and a target role:

- distribution of JRS (histogram, bands) and median
- top 10 missing skills (count of students with `missing`)
- **unverified-claim rate per skill** = students claiming skill at `unverified`/`weak` ÷ students claiming it
- at-risk list: JRS < 50 **or** coverage < 40 %
- understanding summary (each student's top project, latest verify quiz) and per skill the **built-and-explained rate**: students whose claim is `strong`/`moderate` *and* who have a `demonstrated` verify quiz on a project backing that skill ÷ students claiming it
- median readiness by department (`by_department[]`) when departments are set
- CSV export of the above

All computed in SQL / Python from stored analyses; no LLM.
