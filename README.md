<p align="center">
  <img src="docs/assets/logo_k.png" width="160" alt="Kyzo logo">
</p>

<h1 align="center">Kyzo Plan</h1>

<p align="center"><em>You decide what's worth building and write it once — agents execute against that<br>judgment, gated on git, with a judge before every checkbox and a token meter kept lean by design.</em></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-BSL--1.1-6d8074" alt="License: BSL-1.1"></a>
  <a href="#install"><img src="https://img.shields.io/badge/Claude%20Code-plugin-c15f3c" alt="Claude Code plugin"></a>
  <a href="#install"><img src="https://img.shields.io/badge/Cursor-plugin-7fa6bf" alt="Cursor plugin"></a>
  <a href="#a-grammar-not-a-manual"><img src="https://img.shields.io/badge/MCP-35%20typed%20tools-2F7E52" alt="MCP: 35 typed tools"></a>
  <a href="#install"><img src="https://img.shields.io/badge/python-3.12%2B-4B8BBE" alt="Python 3.12+"></a>
  <a href="#where-the-tokens-go"><img src="https://img.shields.io/badge/tokens-watched%20per%20call-b0503b" alt="Tokens watched per call"></a>
  <a href="#install"><img src="https://img.shields.io/badge/config-zero%20by%20default-1E4D33" alt="Zero config by default"></a>
</p>

Kyzo Plan is a control plane for people who still own the product judgment — and for
agents that must not re-derive it. Intent is written once, upstream, as an execution
contract. The board is shared state, not a handoff chain. **35 typed MCP tools**
operate it; git and a completion judge keep motion honest. A checkbox is a fact,
not a self-attestation.

<p align="center"><img src="docs/assets/story_cycle.svg" width="860" alt="One story to Done: start_story, demolition, allowlisted T#s, judge meters dirty tree, parent allowlist-commits, Final QA closes the single DoD box."></p>

## Install

Requirements: [`uv`](https://docs.astral.sh/uv/) on PATH, `gh` authenticated against
the board's GitHub org, Python 3.12+.

**Claude Code**

```
/plugin marketplace add https://github.com/kyzodb/plan
/plugin install kyzo-plan@kyzo
```

Zero config in the common case: board owner and repo come from `origin`, project
number from the repo's sole open linked GitHub Project. `create_board` provisions
a fresh board with this schema if you're starting from nothing.

Overrides on enable (`/plugin configure kyzo-plan@kyzo`) or at install:

```
claude plugin marketplace add https://github.com/kyzodb/plan
claude plugin install kyzo-plan@kyzo \
  --config board_owner=OWNER --config board_repo=REPO --config board_project=N
```

**Cursor** — same skills, agents, and MCP server. Claude Code is the supported
install from this repository today.

Uninstall with `/plugin uninstall kyzo-plan@kyzo`. Board state lives on GitHub;
uninstalling leaves nothing behind.

## One ledger — no translation layer

What you see is what agents operate. Stock GitHub Projects; one screen is the
working truth — not a status chain between roles:

<p align="center"><img src="docs/assets/board_full.png" width="900" alt="The KyzoDB Work board: Backlog, Now, In Progress, Blocked, Next, Later, and Done; epics show roll-up progress bars."></p>

Epics carry roll-up progress (`1 / 3 — 33%`). Classification is the GitHub label.
One card in In Progress answers what is being built right now. Filter `Backlog`
and `Done` away:

<p align="center"><img src="docs/assets/board_condensed.png" width="900" alt="The same board filtered with -status:Done,Backlog."></p>

## Where the tokens go

Agentic cost is mostly **input**: context re-read on every step. Five drains, five
mechanisms — thinking stays upstream; agents don't burn the meter rediscovering it:

<p align="center"><img src="docs/assets/economics.svg" width="860" alt="Where agent tokens go: five drains starved by the story contract, path allowlist and live monitor, demolition first, scoped surfaces, and the judge."></p>

## One axis, horizons on epics

<p align="center"><img src="docs/assets/horizons.svg" width="860" alt="Seven columns on one axis; Now, Next, and Later are epic horizons; a story in In Progress derives its horizon through its parent epic."></p>

## A grammar, not a manual

<p align="center"><img src="docs/assets/grammar.svg" width="860" alt="The name grammar: read_* is pure, start_* finish_* and verify_* are gated, move_to_* is free, authoring writes content, delete_issues is operator-only."></p>

The `kyzo-plan-manage-board` skill carries what lives *between* the tools: orient
with `read_board_status`, never work around a refusal, never touch the board
through raw `gh`.

## The lifecycle refuses until reality agrees

<p align="center"><img src="docs/assets/gates.svg" width="860" alt="start_epic refuses when main is behind origin; start_story refuses out-of-order stories — every refusal names one fact and mutates nothing."></p>

**Branch-per-epic, one story at a time.** The board cannot outrun the repository.
`start_epic` demands a clean, up-to-date `main` and an unused branch. `start_story`
demands `HEAD` on that branch, stories in sub-issue order, and prior work
physically present. `finish_epic` refuses until every box is checked and the
branch has no commit missing from `main` — it verifies the merge; it never
performs it.

## Judgment in, once

The hard work is still yours: what this serves, what dies, what was chosen, and
how done is proven. Skills `kyzo-plan-write-story` and `kyzo-plan-write-epic`
hold the shapes. You commit:

- **Sources / Condemned / Ceiling / Engineering Choice** — the product call,
  crystallized so an agent cannot reopen it as exploration.
- **Context** — exact references; only genuine unknowns marked `[OPEN]`.
- **Tasks** — append-only `T#` with **`Allowlist:`** and a fast **`Check:`**.
- **Definition of Done** — exactly one **Final QA** item (`check_final_qa`). No Witness/CI/worktrees in the contract. Allowlist commit is the seal.

Banned lexicon (*improve, polish, for now…*) stays out of tasks — or lives only
inside Condemned, naming what is being killed. Agents execute the contract; they
do not re-author the judgment.

## Watched at the call

The spawner runs under zero trust: *this agent will deviate; an unwatched
deviation is the spawner's fault.* Paths are law. A live session:

<p align="center"><img src="docs/assets/task_monitor.png" width="900" alt="Orchestrator monitoring a development-task tool-call stream while the task executes."></p>

Orchestration lives in `kyzo-plan-run-story`: allowlist arming, XML spawn, path
watch, parent check, judge after `verify_task_completion`, allowlist commit (the seal),
Final QA + `check_final_qa`.

## Built by Kyzo

Kyzo Plan is the system [KyzoDB](https://github.com/kyzodb/kyzo) is built with —
these screenshots are its live board. It does not use or require KyzoDB. We needed
a control plane we could trust with agents; we built it, we run it every day, and
it earned a release of its own.

Next in the line: **Codegraph** — measuring whether each change moves a codebase
toward the architecture its team intends.

## License

Business Source License 1.1 — free to use, modify, and build on for any
non-production purpose; production use requires a commercial license until the
Change Date, after which it converts to MPL-2.0. See [`LICENSE`](LICENSE).
