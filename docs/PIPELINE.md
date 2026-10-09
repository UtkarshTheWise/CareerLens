# Analysis pipeline and LLM prompts

Design rules:

1. **Small schemas, many steps.** Gemini rejects very large or deeply nested schemas. Each LLM call returns one small object.
2. **LLM extracts and judges; Python scores.** Numbers in the Job Readiness Score come from `SCORING.md`, never directly from a model.
3. **Every LLM and GitHub call is cached** in Postgres keyed by `sha256(model + prompt + input)`, so demo reruns cost nothing and quotas last.
4. **PII is stripped before any LLM call** (regex for emails, phones, URLs with usernames; the name line from the resume header). Re-attach locally.
5. **One gateway**: `llm.generate_structured(schema: type[BaseModel], system: str, user: str, tier: "fast" | "smart")`. Order: Gemini → on 429/5xx Groq (`json_schema` strict) → Ollama if `OLLAMA_URL` is set. Validate with Pydantic; on validation failure retry once with the error appended, then fail the stage gracefully.
6. **No sampling knobs.** `temperature` is deprecated on the newest Gemini models; don't rely on it. Determinism comes from caching.

---

## Stages

| # | Stage | LLM? | Output |
|---|---|---|---|
| 1 | Ingest | No | Resume text (pdfplumber / python-docx, or a UTF-8 `*.txt` built in the app: page count unknown, not penalised), LinkedIn export text, portfolio URLs + Open Graph metadata |
| 2 | Extract resume | Yes (fast) | `ResumeProfile` |
| 3 | Collect GitHub | No | repos, languages, file trees, manifests, contribution calendar, authored-commit counts |
| 4 | Detect | No | per-repo detected skills + quality signals + rule-based flags |
| 5 | Judge projects | Yes (smart, 1 call per project, max 6) | `ProjectJudgement` / `DesignJudgement` |
| 6 | Score | No | `ScoreBreakdown`, claim levels, role fits, gaps |
| 7 | Plan | Yes (fast) | `Roadmap` choosing from `resources.yaml` |
| 8 | Persist | No | `analyses` row with full report JSON; status `done` |

Status is written after each stage (`queued → ingesting → extracting → collecting → detecting → judging → scoring → planning → done | failed`) so the UI can show a live progress list.

### Stage 3 GitHub query (GraphQL, one round-trip for the overview)

```graphql
query($login: String!) {
  user(login: $login) {
    login name bio websiteUrl createdAt
    contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
    repositories(first: 50, ownerAffiliations: OWNER, orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        name description url homepageUrl isFork pushedAt createdAt stargazerCount
        licenseInfo { spdxId }
        primaryLanguage { name }
        languages(first: 10) { edges { size node { name } } }
        repositoryTopics(first: 10) { nodes { topic { name } } }
        defaultBranchRef { target { ... on Commit { history(first: 1) { totalCount } } } }
        readme: object(expression: "HEAD:README.md") { ... on Blob { text } }
        pkg: object(expression: "HEAD:package.json") { ... on Blob { text } }
        req: object(expression: "HEAD:requirements.txt") { ... on Blob { text } }
        pyproject: object(expression: "HEAD:pyproject.toml") { ... on Blob { text } }
        workflows: object(expression: "HEAD:.github/workflows") { ... on Tree { entries { name } } }
        root: object(expression: "HEAD:") { ... on Tree { entries { name type } } }
      }
    }
  }
}
```

Then, for the **top 8 non-fork repos** by recency/size only: the recursive tree (`GET /repos/{o}/{r}/git/trees/HEAD?recursive=1`) for file-based detectors, and authored-commit count via `history(author: {id: $userId})`. Retry `202` responses from stats endpoints with backoff. Cache everything for 24 h.

---

## Prompt templates

All prompts live in `apps/api/app/prompts/*.md` and are loaded by name. Pydantic models in `apps/api/app/schemas/llm.py` define the response schemas below.

### Stage 2: Resume extraction (`extract_resume.md`, tier: fast)

**System**

```
You are a precise resume parser. Extract only what is written. Do not infer, embellish,
or add skills, numbers, dates, or technologies that are not literally present.
If a field is absent, return null or an empty list.
Normalise dates to YYYY-MM when possible, else keep the original string.
"skills" = only items the candidate lists as skills.
"mentioned_technologies" inside each project/experience = technologies named in that item's text.
Return JSON matching the schema exactly.
```

**User**

```
RESUME TEXT (personal identifiers removed):
<<<
{resume_text}
>>>

LINKEDIN EXPORT TEXT (may be empty):
<<<
{linkedin_text}
>>>
```

**Schema `ResumeProfile`**

```json
{
  "headline": "string|null",
  "education": [{"institution": "string", "degree": "string|null", "field": "string|null", "start": "string|null", "end": "string|null", "grade": "string|null"}],
  "skills": ["string"],
  "experience": [{"org": "string", "role": "string", "start": "string|null", "end": "string|null",
                  "bullets": ["string"], "mentioned_technologies": ["string"]}],
  "projects": [{"title": "string", "description": "string", "links": ["string"],
                "mentioned_technologies": ["string"]}],
  "certifications": [{"name": "string", "issuer": "string|null"}],
  "page_count_hint": "integer|null"
}
```

Post-processing (Python): count quantified bullets (`\d+%|\d+x|\d{2,}` etc.), match project links to GitHub repos by URL or fuzzy name.

### Stage 5a: Project judgement (`judge_project.md`, tier: smart)

**System**

```
You review one student project. You receive (a) how the student describes it and
(b) facts measured from its repository. Judge only the DESCRIPTION's specificity and
whether it is consistent with the measured facts. Never speculate about whether text was
written by AI. Never invent facts about the repository. Be kind and concrete: every issue
must come with a fix the student can do in under a day.
Return JSON matching the schema exactly.
```

**User**

```
TARGET ROLE: {role_name}

STUDENT'S DESCRIPTION:
<<<
{project_description}
>>>
TECHNOLOGIES THE STUDENT CLAIMS: {claimed_technologies}

MEASURED REPOSITORY FACTS:
- detected technologies: {detected_skills}
- authored commits: {authored_commits} of {total_commits}; active span: {span_weeks} weeks
- tests: {has_tests}; CI: {has_ci}; demo URL: {homepage}; licence: {license}
- rule flags already raised: {rule_flags}
- README excerpt (first 1500 chars):
<<<
{readme_excerpt}
>>>
```

**Schema `ProjectJudgement`**

```json
{
  "what_it_does": "string (one plain sentence, from facts only)",
  "has_metric": "boolean",
  "has_architecture_detail": "boolean",
  "specificity": "integer 0-3",
  "buzzwords": ["string"],
  "unsupported_claims": ["string (claimed technologies or capabilities not visible in facts)"],
  "issues": [{"issue": "string", "fix": "string"}],
  "honest_rewrite": "string (<= 2 lines, uses ONLY facts above, no new numbers)"
}
```

`vague_description` flag = `specificity <= 1 and not has_metric`. `claim_mismatch` is set in Python from `unsupported_claims` ∩ detector misses (both must agree).

### Stage 5b: Design portfolio item (`judge_design.md`, tier: smart)

**System**

```
You review one design portfolio item from its public page text and metadata. Score the
rubric strictly from what is present on the page. If the page could not be read, say so
and score 0 for that criterion. Do not reward visual adjectives; reward evidence of process
and outcomes. Return JSON matching the schema.
```

**User**: role, item URL, Open Graph title/description, extracted page text (≤ 3000 chars), tools the student claims.

**Schema `DesignJudgement`**

```json
{
  "readable": "boolean",
  "problem_statement": "integer 0-25",
  "process_evidence": "integer 0-30",
  "outcome_or_metrics": "integer 0-20",
  "tool_evidence": "integer 0-15",
  "presentation": "integer 0-10",
  "tools_seen": ["string"],
  "issues": [{"issue": "string", "fix": "string"}]
}
```

### Stage 7: Roadmap planner (`plan_roadmap.md`, tier: fast)

**System**

```
You create a short, ordered improvement roadmap for a student. You may ONLY reference
resource_ids from the provided catalogue and gap_ids from the provided gaps. Never output
URLs. Order milestones by estimated_gain per hour of effort. 4 to 7 milestones.
Each milestone must name a concrete deliverable that would produce new evidence
(a repo, a test suite, a deployed demo, a case study), not "learn X".
Return JSON matching the schema exactly.
```

**User**: role, current JRS and breakdown, gaps `[{gap_id, skill, level, estimated_gain}]`, flags `[{flag_id, project, code, fix, estimated_gain}]`, catalogue `[{resource_id, skill, title, type, hours}]`.

**Schema `RoadmapPlan`**

```json
{
  "milestones": [{
    "title": "string",
    "deliverable": "string",
    "addresses": ["gap_id or flag_id"],
    "resource_ids": ["string"],
    "effort_hours": "integer"
  }]
}
```

Python then validates ids (drops unknown ones), attaches resource URLs from `resources.yaml`, and computes `estimated_gain` via the what-if simulator.

### Job page extraction fallback (`extract_job.md`, tier: fast)

Used only when the extension finds no `JobPosting` JSON-LD.

```
Extract the job posting from this page text. Only copy what is present.
required_skills = explicitly required; nice_to_have = preferred/bonus.
```

**Schema `JobPostingExtract`**: `title, company, location, employment_type, experience_years_min, required_skills[], nice_to_have[], deadline`.

Matching itself is deterministic: normalise JD skills via `skills.yaml`, then
`keyword_match = 100 × matched / required` and `evidence_match = 100 × Σ credit(level) / required` (both 0–100, as in the contract). If no required skills can be identified, use `nice_to_have` as the denominator; if that is also empty, return both as 0 with a summary saying the posting lists no recognisable skills. The extension shows both.

### Truthful tailoring (P2, `tailor_resume.md`, tier: smart)

```
Rewrite resume bullets for this job. Rules:
1. Use only facts in VERIFIED_FACTS. Do not add technologies, numbers, users, or outcomes.
2. You may reorder, shorten, and use the job's vocabulary for skills the student
   has at strong or moderate evidence.
3. If an original bullet contains a number with no supporting fact, keep the bullet but
   add it to "numbers_without_evidence".
Return JSON matching the schema.
```

### Project quiz (on demand, see `docs/QUIZ.md`)

Not part of the analysis run; triggered by `POST /v1/analyses/{id}/quizzes`.

**Generate (`quiz_generate.md`, tier: smart)**

System:

```
You write interview questions about ONE student project, using ONLY the code and text provided.
Goal: check whether the student understands their own project and prepare them for interviews.
Rules:
- Every question except claim_check must cite source_ref that exists in the provided material:
  code projects use (path, start_line, end_line); design projects use (page URL, section heading). Never invent files, functions or behaviour.
- Ask about behaviour, data flow, design trade-offs, failure cases and extensions. Never ask
  trivia answerable by glancing at the snippet (names, line counts, import lists).
- MCQ: 4 options, exactly one correct, distractors plausible for someone who has NOT read the code.
- Short answer: provide 3-5 key_points grounded in the code, plus acceptable_alternatives
  (other valid reasoning). Design-decision questions must accept any coherent, code-consistent reason.
- Wording: neutral and encouraging; never imply the student did not write the code.
Return JSON matching the schema exactly.
```

User: mode, question mix (from QUIZ.md §2), attempt number, project description, claimed technologies, detected skills, claim mismatches, README excerpt, and the key files with line numbers (`<path>\n 1| ...`).

Schema `GeneratedQuiz` (answer keys are stored server-side only):

```json
{
  "questions": [{
    "type": "mcq | short_answer",
    "category": "code_reading | architecture | design_decision | debugging | extension | claim_check | process | outcome | critique",
    "prompt": "string",
    "source_ref": {"path": "string", "start_line": "int|null", "end_line": "int|null", "section": "string|null"},
    "skill_ids": ["string"],
    "options": [{"id": "a", "text": "string"}],
    "correct_choice_id": "string|null",
    "key_points": ["string"],
    "acceptable_alternatives": ["string"],
    "model_answer": "string",
    "hint": "string"
  }]
}
```

Python: drop questions whose `source_ref` isn't in the fetched context (code: the path and line range exist; design: `path` is the fetched page URL and `section` matches a heading or paragraph in the fetched text) or whose MCQ has ≠ 1 correct option; request replacements once; cut `code_snippet` from the cited lines; set time limits.

**Grade (`quiz_grade.md`, verify: tier smart, all answers in one call; practice: tier fast, one answer)**

System:

```
You grade a student's answers about their own project. For each answer and each key point,
return covered, partial or missing. Grade understanding of concepts only: ignore grammar,
spelling, fluency and language (answers may be in Hinglish or any language). If the answer
reaches the goal through an acceptable alternative, mark the matching key points covered.
List incorrect_statements only for claims that contradict the provided code.
Write one short, kind feedback sentence per answer that names what to review.
Return JSON matching the schema exactly. Do not output any score.
```

Schema `QuizGrading`: `answers: [{question_id, key_points: [{text, status}], incorrect_statements: [], feedback}]`. Python computes scores per `QUIZ.md` §3.
