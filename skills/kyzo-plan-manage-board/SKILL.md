---
name: kyzo-plan-manage-board
description: The ONLY way to read or write the work board — plan MCP tools (mcp__plugin_kyzo-plan_board__), never raw gh. Use for any board operation; tool descriptions are the reference.
---

# kyzo-plan-manage-board

Tool schemas are deferred — `ToolSearch` `select:<name>`. This file is only what lives between tools.

**Grammar:** `read_*` pure — orient with `read_board_status`. `start_*`/`finish_*` gated — never work around refusals. `move_to_*` free. Authoring verbs write content. `delete_issues` operator-only.

**Model:** one axis — column + order. Horizons `Later`/`Next`/`Now` are epics. Story horizon derives from parent. Sub-issue order = execution order.

**Lifecycle:** branch-per-epic; one story In Progress. Order: `start_story` → demolition → development tasks. Checkbox only via judge after `verify_task_completion`.

**Spawning work:** use skill `kyzo-plan-run-story` (allowlist arm, XML spawn, path-only monitor, N=5 stall, kill on second offense).
