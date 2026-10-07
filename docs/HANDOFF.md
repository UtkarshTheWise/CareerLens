# Handoff rules and templates

Messages between tracks live in **one file per track**, so two branches (or two laptops) never edit the same file:

| Track | Writes to (append only) | Reads |
|---|---|---|
| Backend | `docs/handoff/backend.md` | the other two |
| Frontend | `docs/handoff/frontend.md` | the other two |
| Integration / human | `docs/handoff/integration.md` | the other two |

Pull `main` before reading the other tracks' logs; they only show what has been merged.

Every agent appends an entry to **its own track's log** when it finishes a task. This file is for **messages between tracks** (requests, CCRs, what the other side can now use). The current state of each track lives in `docs/progress/<track>.md`. Humans approve Contract Change Requests by editing the `Status:` line only (on `main`, in the log where the CCR was written).

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
