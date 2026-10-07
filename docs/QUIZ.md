# Project Understanding Check (project quiz)

The evidence engine can show that code exists and that the student committed it. It can't show that the student **understands** it. The quiz closes that gap: CareerLens generates questions from the student's own repository (their files, their functions, their design choices), grades the answers, and feeds the result back into the evidence levels.

It does two jobs with one engine:

| Mode | Purpose | Timed | Feedback | Affects score |
|---|---|---|---|---|
| **Practice** | Interview prep | No | After every answer: score, model answer, the file/lines it came from | No |
| **Verify** | Prove understanding | Yes | Only after submitting | Yes (see §5) |

Pitch line: *Other tools check your keywords. CareerLens checks your code, then checks that you can explain it.*

---

## 1. Fairness rules (non-negotiable)

1. **A low result never means "you didn't build this".** People forget old code, freeze under a timer, or got help from a teammate on part of a project. The flag is called `understanding_gap`, and the copy says "Understanding not demonstrated yet" with a review list and a retake.
2. **Skipping the quiz is never penalised.** `not_taken` has no effect on the score.
3. **Grade understanding, not English.** Answers in any language (including Hinglish) and with imperfect grammar are graded on concepts only. The grading prompt says so explicitly.
4. **Open-ended design questions have no single right answer.** "Why SQLite?" is graded on whether the reason is coherent and consistent with the code, not on matching our preferred answer.
5. **Results are the student's first.** The placement cell sees only understanding *statuses* (the student's top project in the table, aggregated per-skill rates in the summary), never individual answers, scores per question, or focus/tab data.
6. **Retakes always get fresh questions.** Latest verify attempt counts. One in-progress verify quiz per project. The cooldown (1 hour for the hackathon, 24 h in production) starts when a verify quiz is **created**, so starting quizzes to preview questions doesn't help. A verify quiz left unfinished is auto-submitted (unanswered = 0) once its total time limit plus grace has passed, checked on the next request that touches it.
7. **Symmetric effects.** Whatever a `not_demonstrated` result can take away, a `demonstrated` result on the same skills can give back (§5).

---

## 2. Question generation

### Code context (no LLM)

For the chosen project, collect up to **5 key files**, max 6,000 chars each, 20,000 total:

1. Entry points: `main.py`, `app.py`, `manage.py`, `server.*`, `index.*`, `src/main.*`, `app/page.tsx`, `App.*`.
2. Files that triggered skill detectors (Dockerfile, models, routes, training script…), prioritising skills the student **claims**.
3. The largest non-generated source files the student authored (skip lockfiles, `dist/`, `node_modules/`, migrations, minified files).
4. README (first 2,000 chars) and the student's own project description from the resume.

Fetch with the GraphQL `object(expression: "HEAD:<path>") { ... on Blob { text } }` pattern. Keep line numbers so every question can cite `path:start-end`.

**Design projects** use the case-study page text and the student's description instead of code (§6).

### Question mix

| Category | Type | Verify mode (6 q) | Example |
|---|---|---|---|
| `code_reading` | MCQ (4 options) | 2 | Shows a 10–25 line snippet from *their* file: "What does `rank_candidates()` return when `scores` is empty?" |
| `architecture` | short answer | 1 | "Trace what happens from the moment a user submits the form in `UploadForm.tsx` until the row is saved." |
| `design_decision` | short answer | 1 | "`db.py` uses SQLite. Why that choice, and what would break first with 1,000 concurrent users?" |
| `debugging` | short answer | 1 | "Two requests hit `/checkout` at the same time. What can go wrong in `update_stock()`?" |
| `extension` or `claim_check` | short answer | 1 | Extension: "How would you add pagination to `GET /items`?" · Claim check (if the description names a technology the detectors didn't find): "Your description mentions Redis. Where is it used?" |

Rules:

- MCQ is at most 1/3 of verify questions (guessing is cheap).
- Every question must cite a `source_ref` from the fetched material, except `claim_check`: path + lines for code, page URL + section heading for design. Python drops any question whose `source_ref` doesn't exist in the fetched context, then requests replacements once.
- Questions must not be answerable by reading the snippet alone for 5 seconds. "What is the function name on line 3?" is banned; "what happens when…" is preferred.
- Each short-answer question carries a hidden **answer key**: 3–5 `key_points`, each grounded in the code, plus `acceptable_alternatives` (other valid reasoning).
- Practice mode: up to 10 questions, same categories, plus a `hint`.

The answer key never leaves the server until the quiz is submitted (verify) or the question is answered (practice).

---

## 3. Grading

### MCQ
`1` if correct, else `0`. Deterministic.

### Short answer
One LLM call grades **all short answers of a quiz at once** at submit time (practice: one call per answer). For each key point the model returns `covered | partial | missing`, plus `incorrect_statements[]` (things the student said that contradict the code).

```
q_score = (covered + 0.5 × partial) / key_points  −  0.25 × incorrect_statements      (clamped 0–1)
```

If the answer reaches the same goal through an `acceptable_alternative`, the grader may mark those key points `covered`. Python computes the number; the model only classifies.

### Quiz score
```
quiz = 100 × Σ (w_q × q_score) / Σ w_q        w = 1 for MCQ, 2 for short answer
```

| Quiz score | `understanding` |
|---|---|
| ≥ 70 | `demonstrated` |
| ≥ 40 and < 70 | `partial` |
| < 40 | `not_demonstrated` |

Practice quizzes report the score only (`understanding: null`); they never change evidence.

Unanswered or timed-out questions score 0. All grading calls are cached by `(quiz_id, question_id, answer_hash)`.

---

## 4. Anti-gaming (verify mode)

The student has their repo open on another tab and an LLM a click away. We can't stop that, so the design makes it costly and visible rather than impossible:

- **Time limits**: 60 s per MCQ, 180 s per short answer, enforced **server-side** from the time each question was served (`GET` records `served_at`; answers after limit + 10 s grace score 0).
- **One question at a time**, no going back.
- **Paste disabled** in answer boxes (verify only).
- **Focus-loss count** recorded per question and shown to the student in their result ("You left the tab 3 times"). Not used in the score, not shown to the placement cell. It's a nudge, not an accusation.
- **Questions are about *their* code**, so a generic LLM answer without reading the file tends to miss the specific key points.
- **Fresh questions per attempt**; question generation is seeded by attempt number so the cache doesn't replay old questions.

Be upfront in the pitch: the quiz raises confidence; it doesn't prove authorship. That honesty is itself a point with faculty judges.

---

## 5. Effect on the evidence and the score

Each project gets `understanding` from its latest **verify** attempt. It's stored per project on the profile (keyed by repo URL or portfolio URL) and carried into every later analysis, so re-scanning doesn't wipe a result or a flag.

"Covered skills" below means the `skill_ids` of the quiz's questions. Both the upgrade and the downgrade apply only to covered skills.

| `understanding` | Effect |
|---|---|
| `not_taken` | None. |
| `demonstrated` | **Code:** covered skills at `moderate` from this project → `strong`; authorship & originality +5 (cap 30). **Design:** covered skills at `weak` → `moderate`; design project score +5 (cap 80). Badge "Understanding verified". |
| `partial` | No level change. Review topics listed. |
| `not_demonstrated` | Flag `understanding_gap` (−5 on authorship & originality for code, −5 on the design project score). Covered skills whose **only** evidence is this project drop one level (strong → moderate, moderate → weak). |

Submitting a verify quiz **re-runs the scoring stage only** (no LLM, no GitHub) on the latest analysis and returns `{before, after, delta}`. The report then shows the updated score.

`understanding_gap` flag copy:

- reason: "Your answers didn't yet cover how `<file>` handles `<topic>`."
- fix: "Review `<path>` lines `<a–b>` and `<path2>`; explain the flow to a friend; retake in 1 hour."
- `estimated_gain`: recomputed via `simulate` as if `understanding = demonstrated`.

### Cohort view

`CohortInsights.understanding`: students quizzed, demonstrated, partial, not demonstrated (on each student's top project), and per skill the share of students whose claim is built (`strong`/`moderate`) **and** explained (a `demonstrated` quiz on a project that backs that skill). That's the placement cell's strongest signal: *claimed, built, and explained*.

---

## 6. Design portfolio projects

Same flow, different context: case-study text, the student's description and claimed tools. Categories become `process` (research, iterations), `design_decision` ("why a bottom sheet instead of a modal?"), `outcome` ("what changed after usability testing?") and `critique` ("what would you change for accessibility?"). No MCQ unless the page has enough concrete detail. Because the evidence is self-reported, `demonstrated` doesn't upgrade a design skill beyond `moderate` (§5 lists the symmetric design effects).

---

## 7. Where it shows up

- **Report → Projects**: each project card has "Practice" and "Verify my understanding" buttons and an understanding badge.
- **Quiz screen** (`/quiz/[quizId]`): one question per screen, code snippet with line numbers (from `code_snippet`), countdown ring, progress dots, answer box.
- **Result screen**: quiz score ring, per-question feedback with model answers and links to the exact lines, review topics, the score change, retake button (after cooldown).
- **Roadmap**: an `understanding_gap` becomes a milestone ("Review X, retake verify quiz").
- **Extension (P2)**: on a job page, "Quick practice: 3 questions on your project most relevant to this job".
- **Placement cell**: understanding column in the students table and the cohort summary.

---

## 8. Cost (free tier)

Per verify quiz: **1 smart call** to generate + **1 smart call** to grade all short answers. Practice: 1 generation call + 1 fast call per short answer. Code fetch: ≤ 6 GraphQL calls, cached. Pre-generate and cache the demo personas' quizzes before judging.
