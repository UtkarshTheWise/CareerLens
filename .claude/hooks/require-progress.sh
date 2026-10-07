#!/usr/bin/env bash
# Claude Code Stop hook: don't let a session end with uncommitted work that the
# track's progress file doesn't describe. Exit 2 = block the stop and show stderr to Claude.
input="$(cat)"

# Avoid loops: if Claude is already continuing because of this hook, let it stop.
if printf '%s' "$input" | grep -Eq '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

changed="$(git status --porcelain --untracked-files=all | sed -E 's/^.{3}//; s/.* -> //')"
[ -z "$changed" ] && exit 0                                  # nothing uncommitted
printf '%s\n' "$changed" | grep -q '^docs/progress/' && exit 0   # progress file already updated

cat >&2 <<'MSG'
You have uncommitted changes but haven't updated your track's progress file.
Before stopping, update docs/progress/<backend|frontend|integration>.md per AGENTS.md
("Progress file" section): Status, Resume here, Task board, In-progress detail.
Then commit code + progress file together (use a `wip(...)` commit if the task isn't finished).
MSG
exit 2
