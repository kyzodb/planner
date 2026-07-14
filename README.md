<p align="center">
  <img src="docs/assets/logo_k.png" width="160" alt="Kyzo logo">
</p>

<h1 align="center">Kyzo Planner</h1>

<p align="center"><em>A GitHub Projects board your agents can be trusted with: typed tools,<br>a lifecycle gated on git reality, and a judge between the work and the checkbox.</em></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-BSL--1.1-2F7E52" alt="License: BSL-1.1"></a>
  <a href="#install"><img src="https://img.shields.io/badge/Claude%20Code-plugin-1E4D33" alt="Claude Code plugin"></a>
  <a href="#a-grammar-not-a-manual"><img src="https://img.shields.io/badge/tools-33%20typed-1E4D33" alt="33 typed tools"></a>
  <a href="#install"><img src="https://img.shields.io/badge/config-zero%20by%20default-2F7E52" alt="Zero config by default"></a>
</p>

Agentic development did not shrink the planning problem; it moved it. Code is cheap now. What
stayed expensive is what was always expensive, multiplied by autonomy: knowing what to build next,
in what order, and whether the thing marked done is actually done. An agent's memory is a context
window — it evaporates when the session ends. If the state of work lives in chat scrollback, every
session starts with archaeology and ends with drift.

Kyzo Planner keeps that state in the one place you and your agents can read without translation: a
GitHub Projects board. Not a mirror of the plan — **the plan.** You read it as a kanban board with
roll-up progress bars; your agents operate it as 33 typed MCP tools inside Claude Code. One
artifact, no sync, nothing to go stale.

A plain board, though, is a wall of drag-and-drop state that any process can scribble on. What
makes this one safe to hand to an agent is the shape of the surface:

<p align="center"><img src="docs/assets/glance.svg" width="860" alt="Kyzo Planner at a glance: one board one axis, horizons live on epics, a grammar not a manual, gated against git itself, a checked box is earned."></p>

## The board is the interface

Here is a real one — the live board [KyzoDB](https://github.com/kyzodb/kyzo) is built on:

<p align="center"><img src="docs/assets/board_full.png" width="900" alt="The KyzoDB Work board: Backlog, Now, In Progress, Blocked, Next, Later, and Done columns; epics with roll-up progress bars ride the horizon columns."></p>

Every card carries its signal on its face. An epic shows its stories as a roll-up progress bar
(`1 / 3 — 33%`), classification is the GitHub label itself (`Feature`, `Bug`, `Security`, …), and
the single card in In Progress answers "what is being worked on right now" — with the issue link,
the branch, and the assignee GitHub already renders. Because stories hang under their epics as
sub-issues, the horizon columns hold only epics, yet nothing is hidden: the progress bar *is* the
stories, rolled up.

Day to day, filter `Backlog` and `Done` away and the board collapses to the working truth — the
whole plan in one screen:

<p align="center"><img src="docs/assets/board_condensed.png" width="900" alt="The same board filtered with -status:Done,Backlog: what is active, what is Now, what is Next, what is Later, in one screen."></p>

Nothing here is a custom frontend. It is stock GitHub Projects — visible to anyone you'd show the
repo to, rendered by the tool your team already has open — driven through a surface that keeps it
true.

## One axis, and horizons live on epics

The model has exactly one moving part: which column a card is in, and where it sits within it.
`Now`, `Next`, and `Later` are **horizons**, and horizons belong to epics alone. A story never
stores its own — its horizon is a derived read through its parent epic. That is not a convention
the tools hope you follow; it is the only representable state. There is no field on a story to set,
so a story's schedule and its epic's schedule cannot disagree.

<p align="center"><img src="docs/assets/horizons.svg" width="860" alt="The board model: seven columns on one axis; Now, Next, and Later are epic horizon columns; a story in In Progress derives its horizon through its parent epic."></p>

Order is state too: an epic's sub-issue order **is** its execution order, and card order within a
horizon is priority. Re-planning is therefore one move — pull an epic from `Later` to `Now` and
every story under it just re-planned, with nothing to update and nothing left behind to contradict
it.

## A grammar, not a manual

Thirty-three tools sounds like a manual. It isn't — the surface is an ontology, and a tool's name
tells you its powers before you call it:

<p align="center"><img src="docs/assets/grammar.svg" width="860" alt="The name grammar: read_* is pure, start_* and finish_* are gated, move_to_* is free, authoring verbs write content, delete_issues is operator-only."></p>

Each tool's description is its documentation, so an agent doesn't study a reference — it reads the
schema it was about to call anyway. The `kyzo-planner-manage-board` skill carries the little that
lives *between* the tools: orient with `read_board_status` before acting, never work around a
refusal, never touch the board through raw `gh`.

## The lifecycle refuses until reality agrees

The gated verbs are where this stops being a nicer issue tracker. `start_epic`, `start_story`, and
`finish_epic` run deterministic checks against **git itself** before any mutation, and every failed
check is a typed refusal that names the one fact to fix:

<p align="center"><img src="docs/assets/gates.svg" width="860" alt="A board session: start_epic refuses because main is behind origin, passes after a pull; start_story refuses a story out of sub-issue order, then starts the right one."></p>

The discipline the gates enforce is **branch-per-epic, one story at a time**:

- `start_epic` demands a clean tree on an up-to-date `main`, an unused branch name, and no other
  epic still in flight — then creates the branch, links it to the epic, and pulls the epic into
  `Now`. Epics never enter In Progress; that column belongs to the one active story.
- `start_story` demands `HEAD` on the epic's branch and stories taken in sub-issue order. It also
  demands that the *preceding* story's work physically exists: a story checked off with no commits
  behind it on the branch refuses the next start. The board cannot outrun the repository.
- `finish_epic` closes the loop: every story Done with every box checked, and the epic branch
  carrying no commit missing from `main`. Merging is git work it verifies but never performs —
  your merge strategy stays yours.

Most tools take an optional `target`, so one session can operate several boards; the git gates
always bind to the repository you are actually standing in.

## Stories an agent can execute without re-deriving

The most expensive failure in agent-driven development is not a wrong line of code — it is an agent
re-deriving what was already decided: re-discovering a root cause the author knew, re-confirming a
settled choice, exploring a codebase for a location the story could simply have named. The
exploration reads as diligence and burns tokens by the million.

The story format this plugin ships is built to starve that failure. It is not a ticket template —
it is an execution contract, written once, upstream, by whoever is thinking:

- **Sources** — the authorities this story serves, each with its asserted property.
- **Condemned** — the old path this story kills, why, and the test that proves it stayed dead. The
  demolition agent acts on this block; vague means nothing can be safely deleted.
- **Ceiling** — a `Maximum | Chosen | Constraint` table. Committing below the maximum the sources
  assert requires a *named, measured* constraint — "pragmatism" doesn't parse.
- **Engineering Choice** — the hard commitment, its type, and its consequence. Restated
  uncertainty is not a decision.
- **Context** — exact references (`file`, module, spec) the executor works against, with every
  genuinely open sub-decision marked `[OPEN]` and owned, so improvisation has nowhere to hide.
- **Tasks** — append-only `T#` identifiers, one clause each: the handles the judge checks off.
- **Definition of Done** — including the one item that names the exact verification gate command.
  If you cannot name how done is checked, the story is not sharp enough to execute.

The `kyzo-planner-write-story` and `kyzo-planner-write-epic` skills hold the full contracts,
down to a banned lexicon: mood verbs (*improve, polish, clean up*) cannot appear in tasks, and
escape hatches (*for now, fall back, phase 2*) can appear only inside the Condemned block — naming
the thing being killed.

## The only path to a checked box

Executing a story is a pipeline of three agents with deliberately unequal powers:

<p align="center"><img src="docs/assets/pipeline.svg" width="860" alt="The execution pipeline: story contract, demolition agent, development-task agent, completion judge. Only the judge holds check_story_task; PASS checks the box, FAIL returns a refusal."></p>

- **`kyzo-planner-demolition`** reads the Condemned block and clears the old surface first —
  deleting the files, symbols, and escape routes whose survival would let the next agent wrap or
  route around the design being replaced. It accepts a red tree; a preserved fallback is the
  failure.
- **`kyzo-planner-development-task`** executes exactly one `T#` task. It holds **no board tools**,
  it does not re-derive, and when it believes it is done, all it can do is submit a completion form.
- **`kyzo-planner-task-completion-judge`** is the sole holder of `check_story_task`. It inspects no
  code and infers nothing missing: it rules on submitted evidence against the story contract,
  actively suspicious, burden of proof on the developer. PASS checks the box; FAIL returns a
  refusal naming the missing evidence.

The separation is the point: the agent that wrote the code cannot grade it, and a checkbox on this
board is therefore a *fact* — which is exactly what makes the roll-up progress bars worth reading.

## Install

Requirements: [`uv`](https://docs.astral.sh/uv/) on PATH, `gh` authenticated against the board's
GitHub org, Python 3.12+.

In Claude Code, from a clone (or the repo URL once hosted):

```
/plugin marketplace add /path/to/planner
/plugin install kyzo-planner@kyzo
```

Zero config in the common case: the board defaults to the checkout — owner and repo from the
`origin` remote, project number from the repo's sole open linked GitHub Project. `create_board`
provisions a new board carrying this schema (columns, labels, and descriptions) if you're starting
from nothing.

To target a different board, set the overrides on enable (`/plugin configure kyzo-planner@kyzo`) or
at install time:

```
claude plugin marketplace add /path/to/planner
claude plugin install kyzo-planner@kyzo \
  --config board_owner=OWNER --config board_repo=REPO --config board_project=N
```

When neither config nor a derivable default exists (no origin remote, zero or several open linked
projects), the server refuses to start and names exactly what to set — the same typed-refusal
manner as everything else here.

Uninstall with `/plugin uninstall kyzo-planner@kyzo`. Board state lives entirely on GitHub;
uninstalling leaves nothing behind.

## From the KyzoDB workshop

Kyzo Planner is the system [KyzoDB](https://github.com/kyzodb/kyzo) is built with — the screenshots
above are its live board, and the taste for typed refusals and gated mutations is the same taste
that put seven numbered laws at the front door of that engine. This plugin does not use or require
KyzoDB — yet — and needs nothing but `gh` and `uv`. We are sharing it because the work substrate
turned out to be useful on its own — and if a database whose every answer can be replayed, explained, or
refused sounds like your kind of thing, you know where the board came from.

## License

Business Source License 1.1 — free to use, modify, and build on for any non-production purpose;
production use requires a commercial license until the Change Date, after which it converts to
MPL-2.0. See [`LICENSE`](LICENSE).
