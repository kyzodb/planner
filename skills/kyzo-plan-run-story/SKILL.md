---
name: kyzo-plan-run-story
description: Orchestrate one story or one T# — arm allowlist session, spawn demolition then development under path-only monitoring, submit to the judge. Use when starting or continuing story execution after start_story. Not for writing stories (kyzo-plan-write-story) or raw board edits (kyzo-plan-manage-board).
---

# Run Story (orchestrator)

You are the parent. Child agents will deviate. Unwatched deviation is your fault.

## Before any spawn

1. `read_task_slice(number, task_id)` (or demolition: full Condemned via `read_issues`).
2. Arm the path firewall:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT:-mcp}/scripts/kyzo_arm_session.py <allowlist-paths...>
   export KYZO_TASK_SESSION="$(pwd)/.kyzo/task-session.json"
   ```
3. Spawn with **XML only** — never the full story novel:

```xml
<task_spawn>
  <story>#N</story>
  <task>T# — exact task text</task>
  <allowlist>
    <path>crates/foo/**</path>
  </allowlist>
  <seal>cargo check --workspace --all-targets</seal>
  <condemned>…</condemned>
  <context_refs>…exact paths only…</context_refs>
</task_spawn>
```

## Monitor (path firehose)

Tail **tool name + path/command only** — one short line per call. Never the agent's prose. Never wait for the summary.

| Tell | Action |
| --- | --- |
| path ∉ allowlist | whip (offense +1) |
| whole-file Read / scratchpad tourism | whip |
| board mutate / `check_story_task` from executor | whip |
| 5 tool calls with zero Edit/Write (stall) | whip |
| second offense | **kill** the agent |

Never rehearse their reasons. Done = board checkbox + `verify_task_completion` PASS, never testimony.

## Pipeline

1. `start_story` (if needed)
2. `kyzo-plan-demolition` once
3. For each T#: arm session → spawn `kyzo-plan-development-task` → on their form, spawn judge
4. Judge must call `verify_task_completion` then `check_story_task` on PASS

One T# is not an unbounded grind — batch mechanical migrations; each batch ends in a compile checkpoint.

See `references/gotchas.md` and `references/examples.md`.
