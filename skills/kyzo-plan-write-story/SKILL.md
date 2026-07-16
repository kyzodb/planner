---
name: kyzo-plan-write-story
description: Author or revise board story contracts (name, sources, condemned, ceiling, choice, allowlisted T#s, Final QA DoD). Not epic authorship (write-epic), not T# execution (run-story), not raw board moves (manage-board).
---

# Write Story

A story is an executable engineering commitment. It exposes the value change, its
sources, the condemned path, the ceiling check, the hard engineering choice, and
the evidence required to close the work.

Do not confuse "works" with "correct": a conservative implementation is wrong
when it preserves accidental complexity, duplicate authority, or a low ceiling.
An ambitious choice is valid even when it fails, if the failure produces real
evidence about the product's frontier — the Ceiling section makes that auditable.
Use direct technical language — mechanism, invariant, consequence, proof — never
dramatic quality claims. Every major or minor release gets its own story; its
deliverables are the release notes.

## Executable without re-derivation

The executing agent has exactly two doors: execute the story as written, or stop
and name the blocker. Thinking lives upstream — in this story and in the
orchestrator. A story that makes the agent re-discover a root cause, re-confirm
a settled decision, or hunt the codebase for where a fix goes is under-written.
Three properties enforce this:

1. **Point at a reference.** Name the exact file, module, pattern, or spec the
   agent works against — "compare against `crates/…/canonical.rs`", never "find
   where the codec lives."
2. **Name Allowlist + check on every completion-claiming task.** Each `T#` carries
   indented `**Allowlist:**` paths and `**Check:**` \`fast command\`. Keep it short
   (targeted compile/test). Witness, merge-gate, full CI, and release arbiters do
   **not** belong on the task or in DoD — they are outside Plan. The parent’s
   allowlist commit is the seal after the check passes. Never invent a gate you
   cannot confirm; mark `[OPEN]` if unknown.
3. **Mark decided vs open.** Decided content is immutable and executed as
   written. Anything genuinely undecided is marked `[OPEN]` with who decides,
   and the agent escalates it rather than improvising. Do not manufacture false
   specificity to satisfy this — a named file that is wrong is worse than an
   honest `[OPEN]`.
4. **Bound the cut.** One `T#` is not an unbounded grind. For mechanical
   migrations across many files, write board-level sub-slices (`T5a`/`T5b`, or
   separate tasks) or name orchestrator batches that each end in a compile
   checkpoint — never one agent over 100+ files rediscovering the same symbol.

## GitHub and the board

- A story is a GitHub issue carrying exactly one classification label —
  `Feature`, `Bug`, `Performance`, `Security`, or `Demo` — as the GitHub label
  itself, never restated in the body (a body copy goes stale on the first
  `reclassify_story`).
- Epic membership is the **parent issue** relation (the story is a sub-issue of
  its epic), never a body field.
- **Horizon lives in exactly one place: the parent epic's column** (`Now` /
  `Next` / `Later`). A story never carries its own horizon — no milestone, no
  body field, no label. Milestones do not exist on this board.
- All board writes go through the kyzo-plan-manage-board MCP tools, never raw `gh`.

## Story Schema

Use this exact markdown order. The body opens with the parent-epic cross-link
and a one-sentence lede, then the **human-narrative zone** (Description through
Engineering Choice), then the **executor-contract zone** (Context, Tasks,
Definition of Done). Condemned is a `> [!WARNING]` callout, Ceiling is a table,
Context is wrapped in `<details>`, and each task carries an append-only `T#`
identifier; the remaining field labels are bold `**Label:**` markers that are
both visual skeleton and parser anchors.

```md
# <Story Name>

**Epic:** #<parent-epic-number>

<one plain-language sentence — the lede — introducing this story for a human reader>

## Description

As a <actor>,
I want <capability, invariant, or decision>,
so that <state of value change>.

## Sources

- **<source authority>:** <its asserted property, one line>
- ...every source this story serves.

## Condemned

> [!WARNING]
> **Path:** <old path, fallback, ambiguity, duplicate authority, compatibility path, escape hatch, accidental complexity, low-ceiling implementation, or deferred design this story rejects>
>
> **Reason:** <why this path is unacceptable for correctness, determinism, authority, performance, security, demo credibility, or the product's ceiling>
>
> **Closure test:** <how we know the condemned path is removed, bounded, or mechanically rejected>

## Ceiling

| Maximum | Chosen | Constraint |
| --- | --- | --- |
| <the full-height option the cited sources assert — never invented downward> | <this story's commitment> | <"equal — chosen IS the maximum", or the named measured constraint that forces less, with where that measurement lives> |

## Engineering Choice

**Choice:** <the hard technical commitment this story makes; when it decomposes into parts, write them as a real numbered list, never an inline (1)(2)(3) chain>

**Choice type:** <Representation | Authority Boundary | Execution Currency | Cache Invalidation | Storage Contract | Ordering Invariant | Admission Path | Evaluator Rule | Algorithm | Benchmark | Failure Path | Evidence Boundary>

**Consequence:** <what becomes possible, impossible, measurable, or enforceable because of this choice>

**Evidence needed:** <only for discovery, performance, demo, or evidence-bound stories; otherwise "None">

## Context

<details>
<summary>Execution context</summary>

<Only what is needed to execute and review: mechanisms, constraints, tests, benchmarks, artifacts, failure modes, prior evidence. Point at references by exact name — the file, module, pattern, or spec the executor compares against — so it reads the named slice, never the codebase. Mark any genuinely-undecided sub-decision `[OPEN]` with who decides.>

</details>

## Tasks

- [ ] T1 — <one clause: code, test, artifact, or decision>
  - **Allowlist:** `<path-or-glob>`, `<path>`
  - **Check:** `<exact verification command>`

## Definition of Done

- [ ] Final QA — parent posts VALUE/CONDEMNED/CHOICE/SOURCES verdict then `check_final_qa`
```

`T#` identifiers are append-only: assigned once, never renumbered when a task is
inserted or removed; a new task takes the next unused integer. They are the
handle the kyzo-plan-task-completion-judge checks off, so every task line carries one.

## Rendering

A story serves three readers at once — the operator, the executing agent, and
the parser — and must be scannable in thirty seconds by a reader with no
context. Shape it for the scanning eye:

- **Two zones.** The human-narrative zone (lede → Engineering Choice) reads as
  prose; the executor-contract zone (Context, Tasks, Definition of Done) reads
  as machine spec.
- **Lists over chains.** Any enumeration living inline as `(1)… (2)… (3)…`
  becomes a markdown numbered list.
- **Structure the Context.** `###` sub-heads per topic, a table when the
  evidence is tabular, a `<details>` block for bulk inventories.
- **Backtick every identifier** — paths, commands, crate names, flags, advisory
  ids.
- **One clause per task.** A checkbox packing three actions hides partial
  progress; split compound tasks unless their halves are inseparable evidence.
- Bold nothing except the schema's field labels and true emphasis.

## The story feeds the pipeline

Write each field for its consumer:

- **kyzo-plan-demolition** acts on **Condemned** — concrete delete targets.
- **kyzo-plan-development-task** executes one `T#` (allowlist edits only).
- **Parent (run-story)** runs Check, allowlist-commits, posts Final QA comment, `check_final_qa`.
- **kyzo-plan-task-completion-judge** loads board Check via `read_task_slice`, verifies, then `check_story_task` on PASS.

**Banned in this contract:** git worktrees; Witness / CI / merge-queue as Plan work;
check commands on DoD.

## Field Rules

| Field | Rule |
| --- | --- |
| `Story Name` | Name the domain and value-bearing mechanism, in Title Case. No dramatic quality words. |
| `Description` | `As / I want / so that`; the `so that` clause states a state of value change, not a generic benefit. |
| `Sources` | Every source this story serves, by name, with its one-line asserted property. These are the height reference the Ceiling is judged against. |
| `Condemned.Path` | A concrete rejected path. If the wrong path cannot be identified, the story is not sharp enough. |
| `Condemned.Reason` | Why preserving that path damages the product or lowers its ceiling. |
| `Condemned.Closure test` | Makes the condemned path auditable at completion. |
| `Ceiling.Maximum` | The full-height option the Sources assert. Written from the sources, so falsifying it means falsifying them. |
| `Ceiling.Chosen` | The commitment. Less than Maximum without a real Constraint is a counterfeit story. |
| `Ceiling.Constraint` | `equal`, or a named measured fact (with its location) — never a feeling, a schedule, or "pragmatism". |
| `Engineering Choice.Choice` | Chooses something. Restated uncertainty is not a decision. |
| `Engineering Choice.Choice type` | The closest listed type. |
| `Engineering Choice.Consequence` | What changes because the choice is made. |
| `Engineering Choice.Evidence needed` | May block the final choice only for discovery, measurement, demo-signal, or performance stories; otherwise `None`. |
| `Context` | Only execution/review context. Every reference named by exact path/module/pattern/spec; every undecided sub-decision marked `[OPEN]` with who decides. |
| `Tasks` | One clause each; every code task has `**Allowlist:**` + `**Check:**` (fast only). Commit after PASS is the seal. |
| `Definition of Done` | Exactly one `Final QA …` checkbox. Parent posts FINAL QA comment, then `check_final_qa`. |

## Banned Lexicon

Two mechanically greppable bans:

- **Mood verbs** — improve, harden, polish, finalize, clean up, ensure — banned
  in Tasks.
- **Escape-hatch phrases** — "for now", "initially", "fall back" / "fallback",
  "if needed", "if this proves too hard", "phase 2", "we can later",
  "optionally", "as a first step" — banned in **every section except inside the
  Condemned block, where they name the thing being killed**.

## Invalid Story Conditions

A story is invalid when any of these are true:

* the value change is vague
* the Sources are missing, or the commitment is lower than the sources assert
  without a named measured Constraint in the Ceiling
* the condemned path is missing, abstract, or unauditable
* the Ceiling's Maximum is invented below what the sources assert
* the engineering choice does not choose anything
* both paths remain alive without a named reason and closure boundary
* architecture is deferred without exact deciding evidence
* banned lexicon appears outside the Condemned block
* quality is performed through language instead of proven through mechanism and evidence
* executing it requires re-derivation — no reference named to work against
* DoD is not exactly one `Final QA …` item
* a task check is Witness, merge-gate, full CI, or release arbiter
* the story assumes git worktrees or Plan-owned CI orchestration
* a completion-claiming task lacks `**Allowlist:**` or `**Check:**`
* a live open question is unmarked instead of flagged `[OPEN]`
* it manufactures false specificity — a named file, line, or fix that is not true
