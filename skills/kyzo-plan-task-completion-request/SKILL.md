---
name: kyzo-plan-task-completion-request
description: Form a development-task submits inside completion_request tags to the judge. Use when the seal passed and the tree diff is ready. Not a board write.
---

# Task Completion Request

Submit **only** this block to the judge:

```xml
<completion_request>
STORY: <number>
TASK: T# — <exact board text>
COMPLETION CLAIM: <one sentence>
ALLOWLIST:
- <path>
TREE DIFF:
- COMMAND: git diff --name-only <base>...HEAD
  PATHS:
  - <path>
IMPLEMENTATION:
- <file/symbol>
OBLIGATION PROOF:
- OBLIGATION: …
  EVIDENCE: …   # ≤20 lines; path:symbol preferred
  PROVES: …
CONDEMNED CLOSURE:
- CONDEMNED: …
  PREVENTION: …
  EVIDENCE: …
VALIDATION:
- COMMAND: <exact board Seal — no substitutes>
  RESULT: <exit code + brief>
STORY OR TASK CHANGES: None | …
DEVIATIONS: None | …
</completion_request>
```

Law: VALIDATION.COMMAND must equal board Seal; TREE DIFF must be real and ⊆ ALLOWLIST; empty diff = not done. Judge runs `verify_task_completion` — fake paths die.
