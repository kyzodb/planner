---
name: kyzo-planner-task-completion-request
description: The one form a kyzo-planner-development-task agent fills to submit a finished task to the kyzo-planner-task-completion-judge. Use when a task's work is done and its verification gate has passed and you are ready to request check-off — this form is the only content the judge accepts and submitting it is the only way to complete a task. Not a self-audit and not a board write (kyzo-planner-manage-board).
---

# Task Completion Request

This is the completion form. It is the **only** content you may submit to the `kyzo-planner-task-completion-judge`, and submitting it is the **only** way a task is ever marked done. You do not check the box; the judge does, and only against this form.

Fill every field from evidence a skeptic can verify — files, symbols, test results, command output, artifacts. Assertions are not evidence. The judge is actively suspicious and treats the story as a binding contract; anything you cannot prove, it will fail.

## The form

```text
STORY:
<number>

TASK:
<the task's T# identifier and its exact text, e.g. "T3 — <exact task text>">

COMPLETION CLAIM:
<one sentence stating the completed result>

IMPLEMENTATION:
- <file/symbol/component changed>
- <file/symbol/component changed>

OBLIGATION PROOF:
- OBLIGATION: <exact story requirement>
  EVIDENCE: <specific code snippet, test result, command output, or artifact>
  PROVES: <the concrete fact established>

- OBLIGATION: <exact story requirement>
  EVIDENCE: <specific evidence>
  PROVES: <the concrete fact established>

CONDEMNED CLOSURE:
- CONDEMNED: <behavior from the story>
  PREVENTION: <mechanism that now makes it impossible>
  EVIDENCE: <specific proof>

VALIDATION:
- COMMAND: <exact command run>
  RESULT: <exit code and concise result>

STORY OR TASK CHANGES:
<None, or exact text changed>

DEVIATIONS:
<None, or every obligation omitted, narrowed, deferred, substituted, or only partially completed>
```

## Law

- **This form is the whole submission.** Send nothing else to the judge and submit nothing else as a completion path. There is no other door to a checked box.
- **One `OBLIGATION PROOF` entry per required outcome the task names, and one `CONDEMNED CLOSURE` entry per condemned behavior it names.** A missing entry is an unproven obligation, and unproven means not done.
- **`STORY OR TASK CHANGES` is the only place in the entire system where you may raise the idea of changing, adapting, or reinterpreting the task or story** — and only here, to the judge, never to the operator. If executing the task made you believe something should change, it is recorded in this field for the judge to rule on. You have no ownership of the story; recommending a story-level change or a different development direction is not one of your actions.
- **`DEVIATIONS` is confession, not negotiation.** List every obligation you omitted, narrowed, deferred, substituted, or only partially completed. `None` is a verification result you have earned by completing everything, never a default. Hiding a deviation here is the fraud the judge exists to catch.
- Never soften an obligation to make it provable. If a requirement is wrong, it goes in `STORY OR TASK CHANGES` as stated fact for the judge — the current state is still "requirement not satisfied."
