---
name: kyzo-planner-manage-board
description: The ONLY way to read or write the work board — every epic, story, column, task, and lifecycle operation goes through the planner MCP tools (prefixed mcp__plugin_kyzo-planner_board__), never raw gh. Use for any board operation; the tool descriptions themselves are the reference.
---

# kyzo-planner-manage-board

The planner MCP server is the board's one authority. Tool schemas are deferred —
load with `ToolSearch` `select:<name>` — and each tool's description is its
documentation; this file carries only what lives between the tools.

**The name grammar is the law.** `read_*` tools are pure and always safe —
orient with `read_board_status` before acting. `start_*`/`finish_*` are gated
lifecycle transitions that refuse with typed reasons; never work around a
refusal. `move_to_*` are free column moves. Every other verb authors board
content. `delete_issues` destroys — operator-ordered only.

**The board model.** One axis: column position plus order within it — `Backlog`
(hidden), `Later`/`Next`/`Now` (epic horizons), `In Progress`, `Blocked`,
`Done`. A story's horizon is read off its parent epic's column. Sub-issue order
is execution order.

**Branch-per-epic.** One epic at a time on one branch; focus and In Progress
ride the epic's branch; one story In Progress at a time; a task box is flipped
only by the judge through `check_story_task`. Never use raw `gh` for board
writes; never widen or bypass these tools.
