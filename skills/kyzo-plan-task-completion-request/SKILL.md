---
name: kyzo-plan-task-completion-request
description: Minimal completion_request the development-task sends to the judge after allowlist edits. Not board writes, not git, not tree meters.
---

# Task Completion Request

Submit **only** this block to the judge. Do not invent paths, commands, or git output — the judge loads the board and runs `verify_task_completion`.

```xml
<completion_request>
STORY: <number>
TASK: T# — <exact board text>
COMPLETION CLAIM: <one sentence>
IMPLEMENTATION:
- <path:symbol or file you changed>
DEVIATIONS: None | <what blocked the slice>
STORY OR TASK CHANGES: None | <proposed change — do not apply it>
</completion_request>
```

Done is judge PASS only.
