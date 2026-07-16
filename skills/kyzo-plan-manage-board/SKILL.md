---
name: kyzo-plan-manage-board
description: ONLY board read/write — plan MCP tools, never raw gh. Tool descriptions are role×verb. Not write-story or run-story.
---

# kyzo-plan-manage-board

Tool schemas are deferred — `ToolSearch` `select:<name>`. Between tools:

**Grammar:** `read_*` pure (`read_board_status` first). `start_*`/`finish_*` gated — never stash around refusals. `move_to_*` free. Authoring verbs write content. `delete_issues` operator-only.

**Model:** column + order. Horizons on epics. Story horizon from parent. Sub-issue order = execution order.

**Lifecycle:** `start_story` → demolition → T#s (parent Check + judge + allowlist commit) → Final QA comment → `check_final_qa` → Done.

**Spawning:** `kyzo-plan-run-story`. **Authoring:** `kyzo-plan-write-story` / `kyzo-plan-write-epic`.
