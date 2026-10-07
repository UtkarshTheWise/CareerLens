# HANDOFF log (append only, newest at the bottom)

Every agent appends an entry when it finishes a task. This file is for **messages between tracks** (requests, CCRs, what the other side can now use). The current state of each track lives in `docs/progress/<track>.md`. Humans approve Contract Change Requests by editing the `Status:` line only.

## Entry template

```
### [YYYY-MM-DD HH:MM] <agent: claude-code | codex> — <task id, e.g. B3 / F2>
Changed: <files/areas>
Works: <what can be exercised now, e.g. "POST /v1/profiles/{id}/analyses runs stages 1–6 on fixtures">
Stubbed / mocked: <anything fake>
Needs from other side: <requests>
Checks run: <commands + result>
```

## Contract Change Request template

```
### CCR-<n> [YYYY-MM-DD] by <agent>
Status: PROPOSED   (human sets: APPROVED | REJECTED)
Endpoint/schema: <path or #/components/schemas/X>
Change: <exact YAML diff>
Why: <reason>
Impact: backend <…>; web <…>; extension <…>
```

After APPROVED: the human (or Claude Code in phase 0/3) edits `contracts/openapi.yaml`, runs `pnpm gen:client`, commits `chore(contract): CCR-<n>` to `main`, and both agents rebase.

---

## Log

### [setup] human — Phase 0
Contract v0.1.0 drafted. Awaiting freeze.

### [setup] human — contract v0.2.0
Added Project Understanding Check (docs/QUIZ.md): quiz endpoints and schemas, `understanding_gap` flag, `set_understanding` in simulate, cohort understanding stats. Removed interview-questions endpoint. Awaiting freeze.
