---
name: kyzo-plan-run-story
description: Parent after start_story — arm paths, spawn demolition then each T#, run board Check, spawn judge, allowlist-commit on PASS / path-restore on FAIL, Final QA verdict then check_final_qa. Not write-story or manage-board.
---

# Run Story (parent)

Children deviate. Unwatched deviation is your fault.

## Role×verb

| You | Children never |
| --- | --- |
| `start_story`, arm session, spawn, path-monitor | git, Bash, board mutate, `check_story_task` |
| Run board **Check** before judge | invent a greener check |
| Allowlist-only commit after judge PASS (that commit is the seal) | stash / hard-reset / worktree / off-list commit |
| Path restore on FAIL | |
| Final QA verdict (comment) then `check_final_qa` | skip the written verdict |
| `move_to_done` | Witness / CI orchestration |

One epic branch. One writer at a time.

## Arm

```bash
python3 ${CLAUDE_PLUGIN_ROOT:-mcp}/scripts/kyzo_arm_session.py <paths...>
export KYZO_TASK_SESSION="$(pwd)/.kyzo/task-session.json"
```

## Demolition (once)

1. Read Condemned; list concrete paths to delete.
2. Arm those paths. Spawn `kyzo-plan-demolition` with XML naming only those paths + condemned text.
3. Monitor: Edit outside armed paths → whip; second offense → kill. Preservation edits → kill.

```xml
<demolition_spawn>
  <story>#N</story>
  <allowlist>
    <path>…condemned path…</path>
  </allowlist>
  <condemned>…</condemned>
</demolition_spawn>
```

## Each T#

1. `read_task_slice` → arm Allowlist paths.
2. Spawn `kyzo-plan-development-task`:

```xml
<task_spawn>
  <story>#N</story>
  <task>T# — exact board text</task>
  <allowlist>
    <path>…</path>
  </allowlist>
  <check>…exact board Check…</check>
  <context_refs>…</context_refs>
</task_spawn>
```

3. Monitor (path + tool name only):

| Tell | Action |
| --- | --- |
| path ∉ allowlist | whip |
| Bash / git / board mutate / `check_story_task` | whip; second → kill |
| 5 tools, zero Edit/Write | whip |
| second offense | kill |

4. Run the board Check command exactly. Red inside allowlist → send back or kill. Red from foreign tree → escalate (never stash).
5. On green: spawn judge with the child's `<completion_request>` only.
6. Judge PASS → `git add -- <allowlist paths only>` → one commit (`T# — …`). Then next T#.
7. Judge FAIL → `git restore --worktree --staged -- <allowlist paths only>`. Never `reset --hard` / stash.

## Final QA (after every T# checked)

Write a story comment:

```
FINAL QA
VALUE: …
CONDEMNED: …
CHOICE: …
SOURCES: …
```

Then `check_final_qa` → `move_to_done` (or next story).

Dirty tree at `start_*` → escalate to operator. Stash to pass a gate = fraud.

See `references/gotchas.md` and `references/examples.md`.
