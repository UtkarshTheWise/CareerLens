# apps/api — backend rules (owner: Claude Code)

Stack: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (or SQLModel) + Alembic, httpx, pdfplumber, python-docx, google-genai, groq, PyYAML, pytest, ruff. Managed with `uv`.

## Layout

```
apps/api/
  app/
    main.py              # app factory, CORS, routers, /health
    config.py            # pydantic-settings; reads .env
    deps.py              # db session, auth (DEV_AUTH bypass)
    routers/             # one file per contract tag: profiles, analyses, jobs, applications, cohorts, meta
    schemas/api.py       # Pydantic models mirroring contracts/openapi.yaml EXACTLY
    schemas/llm.py       # small LLM response schemas from docs/PIPELINE.md
    db/models.py         # tables: profiles, documents, analyses, applications, cohorts, quizzes, quiz_questions (answer keys), quiz_answers, cache
    services/
      ingest.py          # pdf/docx → text, PII stripping
      github.py          # GraphQL + REST tree, 202 retry, 24h cache
      detectors.py       # skills.yaml detectors, repo quality signals, rule flags
      llm.py             # generate_structured(): Gemini → Groq → Ollama, cache, retry-on-validation
      scoring.py         # pure functions from docs/SCORING.md (no I/O)
      planner.py         # roadmap: LLM picks ids, Python attaches resources + gains
      matching.py        # job keyword_match / evidence_match
      cohorts.py         # cohort aggregates
      quiz_context.py    # key-file selection + fetch for quizzes (docs/QUIZ.md)
      quiz.py            # generate, time, grade, apply understanding, re-score
      pipeline.py        # runs stages, writes status after each
    prompts/*.md         # templates from docs/PIPELINE.md
  scripts/
    check_contract.py    # diff app.openapi() against contracts/openapi.yaml (paths, methods, schema names, required fields, enums)
    seed_demo.py         # demo profile + synthetic cohort of ~40 students with stored analyses
  tests/
    fixtures/            # sample resume text, recorded GitHub JSON, recorded LLM JSON
```

`data/` (repo root, also owned by Claude Code): `skills.yaml` (~60 skills with detectors), `roles.yaml` (7 roles: sde-backend, sde-frontend, full-stack, data-analyst, ml-engineer, devops-cloud, ui-ux-designer), `resources.yaml` (real, well-known free resources only, ≥ 2 per skill), `tutorial_names.txt`, `readme_templates.txt`.

## Rules

- `scoring.py` is pure and fully unit-tested. Same input → same output. No LLM calls inside it.
- Tests never hit the network: use recorded fixtures for GitHub and LLM. Mark live tests `@pytest.mark.live`.
- Every LLM call goes through `llm.generate_structured`. Every external call is cached in the `cache` table.
- Long work runs in `BackgroundTasks` (prototype) with status writes per stage; endpoint returns 202 immediately.
- Errors use the contract's `Error` shape `{code, message, details}` via an exception handler.
- `DATABASE_URL` may be SQLite locally and Supabase Postgres in deploy; avoid Postgres-only SQL except in cohorts, which must also work on SQLite.
- CORS: `allow_origins=CORS_ORIGINS` plus `allow_origin_regex=r"chrome-extension://.*"` (CORSMiddleware does not accept wildcards in the list).
- Log stage timings; never log resume text or tokens.
- Quiz answer keys (`correct_choice_id`, `key_points`, `model_answer`) are never serialised before that question is graded. Focus-loss data is visible only to the student.
