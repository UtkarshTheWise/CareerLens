# AGENTS.md — shared rules for every coding agent (Codex and Claude Code)

CareerLens: evidence-based employability analyser (resume + GitHub + portfolio → explainable Job Readiness Score, gaps, roadmap, placement-cell cohort view, Chrome extension). Read `README.md` for the product, `docs/SCORING.md`, `docs/PIPELINE.md` and `docs/QUIZ.md` for logic, `docs/DESIGN.md` for UI.

## Ownership (hard rule)

| Path | Owner | Others may |
|---|---|---|
| `contracts/openapi.yaml` | Human (drafted by Claude Code) | read only |
| `packages/api-client/schema.d.ts` | generated | never hand-edit; run `pnpm gen:client` |
| `packages/api-client/` wrapper (`index.ts`, `package.json`) | written once by Claude Code in Phase 0, then Codex | — |
| `apps/api/`, `data/` | Claude Code | read only |
| `apps/web/`, `apps/extension/` | Codex | read only |
| `docs/handoff/<track>.md` | that track | read; **append only** to your own |
| root `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml` | Codex | request changes in your handoff log |
| `apps/api/uv.lock` | Claude Code | — |

If you need something outside your area, **do not edit it**. Append a request to your track's `docs/handoff/<track>.md` and continue with a stub or mock.

## The contract is the source of truth

- All HTTP shapes come from `contracts/openapi.yaml`. Do not invent endpoints, fields or enum values.
- Frontend uses only the generated client in `packages/api-client`. No hand-written duplicate types of API models.
- Backend Pydantic models must serialise to exactly the contract's shapes. `apps/api/scripts/check_contract.py` must pass.
- Need a change? Write a **Contract Change Request** in your track's handoff log (template in `docs/HANDOFF.md`) and stop work on that piece until a human approves.

## Product rules (apply to code, copy and prompts)

- Never call a student's work "AI slop", "larping", "fake" or "dishonest". Use: *Evidence Coverage*, *Unverified claim*, *Low-evidence project*.
- Never claim to detect AI-written text.
- A weak quiz result is "understanding not demonstrated yet" (flag `understanding_gap`), never "didn't build it". Skipping a quiz never lowers a score.
- Every score shown must be explainable: show the `reasons[]` behind it.
- Never invent URLs, metrics or skills. Resources come from `data/resources.yaml`.
- Strip personal identifiers before any LLM call. Demo data is synthetic.

## Progress file (context hand-off) — mandatory

Any agent or model may be swapped in mid-task when another hits its usage or context limit. Your track's progress file is how the next one continues without re-deriving everything.

| Track | File |
|---|---|
| Backend (`apps/api`, `data/`) | `docs/progress/backend.md` |
| Frontend (`apps/web`, `apps/extension`) | `docs/progress/frontend.md` |
| Integration (Phase 3) | `docs/progress/integration.md` |

1. **Read it first**, before any other work, every session. If it disagrees with `git log` / `git status` / the checks, trust git and the checks and correct the file.
2. **Update it after every meaningful step** (a file finished, a test passing, a decision made), not only at the end. Limits cut sessions off without warning.
3. **"Resume here" must be executable by a model with zero context**: exact file, function, what's left, and the next command to run.
4. Overwrite *Status*, *Resume here*, *Task board* and *In-progress detail* so they show the truth now. Append one-liners to *Decisions* and *Gotchas*. Keep it under ~150 lines.
5. **Commit it with the code it describes.** Unfinished work goes in a `wip(<area>): …` commit on your own branch so the next agent can see it.
6. Write `Last updated` with your agent and model name (e.g. "Codex (gpt-…)", "Claude Code (Opus …)").
7. Mark half-built code with `TODO(progress): <what's missing>` and list it under *Stubbed / fake*.
8. Only edit your own track's file. Cross-track requests go in your `docs/handoff/<track>.md`.

`docs/progress/*.md` = current state of one track (overwritten). `docs/handoff/<track>.md` = messages from that track to the others (append-only). Neither is ever edited by another track, so branches on different machines merge cleanly.

## Workflow

- Work on your own branch/worktree: `backend/claude` or `frontend/codex`. Small commits, conventional messages (`feat(api): …`, `fix(web): …`).
- Before finishing any task: run the checks for your area (below) and append a short entry to your `docs/handoff/<track>.md` (what changed, what's stubbed, what you need).
- **Push after every commit** (`git push`), including `wip` commits. Tracks may run on different laptops; unpushed work is invisible and lost if a machine dies.
- After any contract change lands on `main`: `git pull --rebase origin main` then `pnpm gen:client`.
- Don't add dependencies without saying why in your handoff entry.
- Never commit `.env*` files or keys. Never print secrets in logs.

## Commands

```bash
# contract
npx @stoplight/prism-cli mock contracts/openapi.yaml -p 4010 -d   # mock API
pnpm gen:client                                                     # regenerate packages/api-client

# backend (apps/api)
uv sync && uv run fastapi dev app/main.py
uv run pytest -q && uv run ruff check . && uv run python scripts/check_contract.py

# web (apps/web)
pnpm --filter web dev | build | lint | typecheck

# extension (apps/extension)
pnpm --filter extension build     # then chrome://extensions → Load unpacked → apps/extension/dist
```

## Environment

- Backend URL for frontend: `NEXT_PUBLIC_API_URL` (`http://localhost:4010` = mock, `http://localhost:8000` = real).
- Extension API URL is set on its options page (default `http://localhost:8000`).
- Dev auth: backend with `DEV_AUTH=1` accepts any request and uses the demo profile from `GET /v1/me`.

## Done means

Your area's checks pass, the app runs, nothing outside your area changed (`git diff --stat main...HEAD`), your progress file shows the task as `done` with its commit, your handoff log is updated, and everything is pushed.
