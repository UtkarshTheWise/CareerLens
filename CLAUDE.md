@AGENTS.md
@apps/api/AGENTS.md

# Claude Code specifics

You are the **contract drafter** (phase 0), **backend owner** (phase 1) and **integrator** (phase 3). See `PROMPTS.md` for which phase you are in; the human will say it.

- Start every non-trivial task in plan mode and wait for approval before editing.
- Phase 1: the backend worktree has `.claude/settings.local.json` (copied from `backend.settings.local.json`) denying edits to `apps/web/**`, `apps/extension/**` and `packages/api-client/**`. Don't try to work around it (no Bash writes there either).
- Phase 3 (integration, main checkout, no local deny file): your job is wiring, contract drift fixes and bug fixes, **not** new features or redesigns. Prefer fixing the backend to match the contract over changing the frontend.
- A Stop hook (`.claude/hooks/require-progress.sh`) blocks ending a session while there are uncommitted changes and your `docs/progress/` file isn't updated. Update the file; don't try to bypass the hook.
- When the context gets long or before `/compact`, run the CHECKPOINT prompt from `PROMPTS.md` first.
- Use subagents for broad searches and for the final review, so the main context stays clean.
- After any change to routes or schemas run `uv run python scripts/check_contract.py`.
- Branches: `main` (phase 0), `backend/claude` (phase 1), `integration` (phase 3). Conventional commit messages.
