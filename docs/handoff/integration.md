# Handoff log — integration track (append only, newest at the bottom)

Templates and rules: `docs/HANDOFF.md`. Only the integration track writes here.

### [setup] human — Phase 0
Contract v0.1.0 drafted.

### [setup] human — contract v0.2.0
Added Project Understanding Check (docs/QUIZ.md): quiz endpoints and schemas, `understanding_gap` flag, `set_understanding` in simulate, cohort understanding stats. Removed interview-questions endpoint. Awaiting freeze.

### [2026-10-07 13:57] claude-code — P0 contract freeze v0.2.0
Changed: `contracts/openapi.yaml` (review changes + examples), root `package.json` / `pnpm-workspace.yaml` / `pnpm-lock.yaml`, `packages/api-client/` (wrapper + generated `schema.d.ts`), `apps/api/.env.example`, `redocly.yaml`.
Contract changes since the draft:
- New: `GET /v1/quizzes/{quiz_id}/result` (re-fetch a submitted or auto-submitted quiz result), `PATCH /v1/analyses/{analysis_id}/roadmap/{milestone_id}` (`{done}`), `QuizStatus` schema, `default` Error response on every operation.
- Renamed: `ProjectAudit.repo_url` → `url` (repo URL for code, portfolio page URL for design).
- Added fields: `ProjectAudit.demo_url`, `counted_in_score` (required), `design_subscores`, `signals`, `issues`; `SkillGap.claimed` (required); `AnalysisSummary.verified_skills`; `QuizQuestion.time_remaining_s`; `QuizAnswerFeedback.choice_id`, `text`; `CohortStudent.github_username`, `analysis_id`.
- Tightened: `AnalysisStatus.progress` is required. Removed `more_commits` from `SimulationRequest…add_signals`. createQuiz 429 detail key is `details.retake_available_at`.
- Fixed: five flow-style descriptions containing commas were parsing as extra schema keys; now quoted.
Works: static Prism mock returns one consistent synthetic persona (CSE student, sde-backend, JRS 65.1) for analyses, roles, me, cohort insights/students and job match.
Stubbed / mocked: everything; no backend code yet.
Needs from other side:
- Codex: root package files are yours from here. Run the mock without `-d`. Add `transpilePackages: ["@careerlens/api-client"]` to the Next config. Use `time_remaining_s` for the verify countdown, not the client clock. `ApplicationCreate.company` is required but `JobPosting.company` can be null: fall back to the page hostname when saving from the extension.
- Backend: implement the two new endpoints (B6 roadmap PATCH, B9 quiz result). Keep the example skill ids in `data/skills.yaml`. Install `uv` on this machine before B1.
- Human: AGENTS.md and RUNBOOK.md still show the mock command with `-d`; drop the flag there. Tag `v0.2.0`.
Checks run: `npx @redocly/cli lint contracts/openapi.yaml` valid (examples validated against their schemas); `pnpm gen:client` ok; `pnpm exec tsc --noEmit -p packages/api-client` ok; Prism `-d` starts and serves `/v1/roles` 200 with `Authorization: Bearer dev`, 401 without; static mode same plus persona data. `check_contract.py` not run (does not exist until B1).
