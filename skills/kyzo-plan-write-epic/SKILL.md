---
name: kyzo-plan-write-epic
description: Author or revise board epics — name + outcome as the value state the story group creates. Not story contracts (write-story), not T# runs (run-story), not column moves (manage-board).
---

# Write Epic

An epic is a group of stories that together create a state of value change. A
valid epic explains why the grouped stories belong together and what
engineering/value condition changes when they are complete. Write the outcome as
a transition: what the product is moving from, what it is moving to, and what
shared technical boundary, authority, capability, proof, or failure class the
grouped stories cross.

Do not write epics as release slogans, phases, status buckets, or heroic quality
claims. The epic does not use story format: no tasks, no Definition of Done. The
stories carry execution; the epic carries grouping meaning.

## The epic's place in the system

The epic carries three things and only three: the **grouping meaning** (its
outcome paragraph), the **horizon** (its board column), and the **execution
order** (its sub-issue order). That triple is the plan the orchestrator reads.

The epic carries **no execution detail** — no file paths, no fixes, no
verification commands, no tasks. Those live in the stories, because the story is
what an agent executes and the epic is not. Precision has one home per altitude:
grouping and order here, references and verification gates in the stories (see
`kyzo-plan-write-story` → "Executable without re-derivation").

## Epic Schema

Use this exact markdown order: a one-sentence lede, the Outcome Description in a
`> [!NOTE]` callout, and a `## Stories` cross-link list mirroring the epic's
sub-issues in execution order.

```md
# <Epic Name>

<one plain-language sentence — the lede — introducing this epic for a human reader>

## Outcome Description

> [!NOTE]
> <One paragraph describing the transition this group of stories creates. State what the product is moving from, what it is moving to, and what shared technical boundary, authority, capability, proof, or failure class makes these stories belong together.>

## Stories

- #<story-number>
- ...every story sub-issue of this epic, in execution order
```

The `## Stories` list is a **rendered mirror of the sub-issue graph** — the
graph remains the authority for membership and order; the list is regenerated
from it, never hand-maintained as a second source of truth.

## GitHub and the board

- An epic is a GitHub issue; its stories are attached as **sub-issues** of it,
  and sub-issue list order is the execution order.
- The epic carries exactly one of the five labels — `Feature`, `Bug`,
  `Performance`, `Security`, or `Demo`, matching the dominant character of its
  stories — as the GitHub label itself, never restated in the body.
- **The epic is the one carrier of horizon, and it carries it as column
  position** (`Now` / `Next` / `Later`, moved via the kyzo-plan-manage-board
  tools) — never as a milestone or a body field. Milestones do not exist on this
  board. Its stories read their horizon through the parent relation and never
  carry their own.

## Rendering

The outcome is one paragraph, and a reader with no context must get the
from → to arc in a single pass: two or three real sentences, not one 150-word
sentence chained with em-dashes. Backtick every path, crate, and command. The
lede sits above the callout as the one sentence read first; the `## Stories`
list cross-links each child as `#N`, which GitHub renders as a live link. Bold
nothing — the epic's structure is the lede, the callout, and the list.

## Field Rules

| Field | Rule |
| --- | --- |
| `Epic Name` | Name the value boundary being crossed by the group of stories, in Title Case. Not a mood, phase, slogan, release ceremony, or generic work category. |
| `Outcome Description` | The aggregate state of value change the grouped stories create: why they belong together and what condition changes when they are done. |

## Invalid Epic Conditions

An epic is invalid when any of these are true:

* the name is a slogan, phase, or mood
* the outcome only says work will be completed
* the outcome does not explain why the stories belong together
* the outcome does not describe a transition from one engineering/value condition to another
* the epic uses story format, or includes tasks or a Definition of Done
* the epic leaks story-level execution detail — file paths, fixes, verification
  commands, reference pointers
* the body restates the label, or carries a milestone or horizon field — those
  live on the GitHub label and the board column, nowhere else
* the language performs quality instead of naming the shared boundary,
  authority, capability, proof, or failure class
