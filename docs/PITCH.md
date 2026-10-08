# CareerLens: pitch for the judges

**Team Eucalyptus (082):** Utkarsh Mishra, Vatshal Pandey, Adwit Tiwari, Samarth Premchandani, Aarav Agarwal
**Live:** https://career-lens-sigma.vercel.app · **Target length:** 5 minutes + questions

---

## One line

> CareerLens shows students, and the people who place them, how ready they really are for a job: a score built from the work they have actually done, with every point explained.

## The problem (30 seconds)

- A resume says "Python, Docker, Kubernetes". Nobody, including the student, can tell which of those are backed by real work.
- Placement cells see only resumes, so they cannot tell which students need help until it is too late.
- Students get advice like "improve your skills" with no idea which skill, which project, or what to do first.

## What CareerLens does (45 seconds)

1. **Reads the evidence.** Resume + GitHub + portfolio, compared against what the target role needs (7 roles, ~60 skills).
2. **Scores it, and shows its working.** A Job Readiness Score out of 100 built from five components. Every component lists the reasons behind it. No unexplained numbers.
3. **Separates claims from evidence.** Each skill is marked strong / moderate / weak / unverified, with links to the repository or file that supports it. We call the gap an **Unverified claim** or **Low-evidence project**, never anything accusatory.
4. **Checks understanding, kindly.** An optional quiz on the student's own project code. A weak result means *"understanding not demonstrated yet"*, never *"you didn't build this"*, and skipping a quiz never lowers a score.
5. **Gives a next step.** A roadmap ordered by score gain per hour, with free resources only from a curated list. We never invent links.
6. **Meets students where they apply.** A Chrome extension compares any job posting with their evidence and saves it to a tracker.
7. **Gives the placement cell the cohort view.** Where the cohort stands, which skills everyone claims but nobody can show, and who needs help first.

## Live demo (2.5 minutes)

| Time | Show | Say |
|---|---|---|
| 0:00 | Home page → **Get started** → Google sign-in | "One account, one click." |
| 0:20 | Dashboard / report of the pre-analysed demo student | "72 out of 100. Click any component and it tells you why." |
| 0:50 | Skill claims with evidence links; one **Unverified claim** | "Docker is on the resume but no repository shows it. That is the gap, stated fairly." |
| 1:10 | **What-if**: toggle tests / CI on a project | "Add tests and CI and the score moves by this much. That is the plan." |
| 1:30 | **Roadmap** + a free resource | "Sorted by gain per hour. Resources come from a vetted list." |
| 1:45 | **Quiz** result screen (pre-generated) | "A weak answer says 'not demonstrated yet'. It never calls anyone a fraud." |
| 2:05 | **Extension** on a job page → match + save to tracker | "Same evidence, at the moment of applying." |
| 2:30 | **Placement view** (staff account) | See the next section. |

> Do not generate a new analysis live. It makes ~8-12 model calls and can take 1-2 minutes on the free tier. Show the pre-analysed student, and say "this ran earlier".

## Placement cell: how to present the cohort view (1 minute)

Open **Placement cell** with the staff account. Use a cohort of **40 synthetic students** (invented names, no real data).

1. **The headline:** "Of 40 students, about a third are not ready yet, under half are developing, and a quarter are ready." (Read the bands and the histogram on screen.)
2. **The pattern:** point at **Top missing skills** and the **Unverified-claim rate**. "Most students list Docker and Kubernetes. Almost none can show Kubernetes in a repository. That is one workshop, not forty one-to-one conversations."
3. **Who first:** apply the **at-risk filter** on the students table. "These are the students to talk to this week."
4. **Understanding:** the summary shows how many students have taken a quiz and how many demonstrated understanding, as a status only.
5. **Take it away:** **Download CSV**.

Privacy points to say out loud: the cohort view shows scores, bands and a quiz *status*, never a student's answers or quiz behaviour. Only staff accounts can open it.

## Why this is different

- **Explainable by design.** Every score has reasons; every skill has evidence or is marked unverified.
- **Fair by design.** No "AI-written" detection, no accusations. Weak quiz results are an invitation to review, not a verdict.
- **Private by design.** Names, emails, phone numbers and links are stripped before any text goes to a model. A student can delete their data. Demo data is synthetic.
- **Honest sources.** Resources come from a curated list; the system is not allowed to invent URLs, metrics or skills.
- **Works for the student and the institution.** Same engine, two views.

## How it is built (for technical questions)

- **Backend:** FastAPI, Pydantic v2, SQLAlchemy, Postgres (Supabase). Scoring is pure, deterministic Python (same input, same score); the models only read text and write questions.
- **AI:** Gemini → Groq fallback, structured JSON output validated against schemas, 24-hour cache. Students can add their own key so the shared free quota doesn't run out.
- **Web:** Next.js, generated typed client from an OpenAPI contract. **Extension:** Chrome MV3 side panel.
- **Auth:** Google sign-in through Supabase; staff-only cohort routes.
- **Quality:** a frozen API contract checked in CI-style script (29/29 operations), 683 backend tests, a 499-check end-to-end smoke test in two auth modes.
- **Hosting:** Vercel (web), Render (API), Supabase (database and auth), all on free tiers.

## Honest limits (say them before they ask)

- The free model quotas are small. Live analysis can be slow or rate-limited, so we demo from a prepared student, and users can bring their own key.
- The GitHub username is self-declared; the quiz is the check that the student understands the work.
- The extension is loaded manually (not on the Chrome Web Store yet); the site has an install guide.
- The cohort view uses synthetic students. Letting real students join a cohort (a join code) is the next feature.
- The first request after idle takes up to a minute while the free server wakes.

## Likely questions

- **"Isn't this just an LLM reading a resume?"** No. The score comes from deterministic rules over evidence we collect (commits, tests, CI, deployment, README quality). The model reads text and writes questions; it never decides the score.
- **"Can students game it?"** Padding a resume doesn't move the score; only evidence does. The optional quiz tests whether they can explain their own code. Gaming it means doing the work.
- **"Can a student fake a GitHub account?"** Today the username is self-declared; GitHub sign-in or a verification gist is the planned fix, and the quiz is the mitigation.
- **"What about bias or unfairness?"** No names or personal details reach the model, quiz results never lower a score by being skipped, and wording is deliberately non-accusatory.
- **"What would you do next?"** Join codes for real cohorts, GitHub sign-in, a Chrome Web Store listing, and a paid model tier to remove the quota limit.

## Before you walk on stage

- [ ] Open `<api>/health` once (wakes the Render server; wait for 200).
- [ ] Sign in with the **demo student** account and confirm the report loads; sign in as the **staff** account in a second browser profile and confirm the Placement cell shows 40 students.
- [ ] Quizzes pre-generated; the extension loaded and signed in; a Greenhouse or Lever job page open in a tab.
- [ ] Your own AI key saved in Settings, in case anything is regenerated.
- [ ] Dark theme or light theme chosen, laptop on charge, notifications off.
