"""The story's own contract: what a story's body must contain to construct at all, and the two-way
crossing between that proven shape and the markdown GitHub actually stores."""

import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

from app.domain.type import (
    Actor,
    CeilingChosen,
    CeilingConstraint,
    CeilingMaximum,
    Choice,
    ChoiceType,
    ChoiceTypeName,
    ClosureTest,
    CondemnedPath,
    CondemnedReason,
    Consequence,
    EvidenceText,
    IssueLabel,
    IssueNumber,
    LedeLine,
    SoThat,
    SourceEntry,
    StoryContext,
    TaskId,
    TaskText,
    Want,
)
from app.domain.value import Condemned, EngineeringChoice, EvidenceNotNeeded, EvidenceStated, StoryDescription

SECTION_ORDER = (
    "Description",
    "Sources",
    "Condemned",
    "Ceiling",
    "Engineering Choice",
    "Context",
    "Tasks",
    "Definition of Done",
)


class SourcesList(RootModel[tuple[SourceEntry, ...]], frozen=True):
    """Every source a story serves — the height reference its Ceiling is judged against."""

    root: tuple[SourceEntry, ...] = Field(min_length=1)


class Ceiling(BaseModel):
    """The ceiling check: the sources' full-height maximum, this story's commitment, and the named
    constraint when the commitment is less."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    maximum: CeilingMaximum
    chosen: CeilingChosen
    constraint: CeilingConstraint


class Task(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    checked: bool
    text: TaskText
    tid: TaskId | None = None

    @property
    def markdown(self) -> str:
        box = "x" if self.checked else " "
        if self.tid is not None:
            return f"- [{box}] {self.tid.rendered} — {self.text.root}"
        return f"- [{box}] {self.text.root}"


class TaskIdRefusal(Exception):
    """A task-id check-off that cannot be honored, carried as a typed value the caller branches on."""


class TaskIdNotFound(TaskIdRefusal):
    def __init__(self, tid: TaskId) -> None:
        super().__init__(f"no task carries identifier {tid.rendered}")
        self.tid = tid


class TaskIdAmbiguous(TaskIdRefusal):
    def __init__(self, tid: TaskId, count: int) -> None:
        super().__init__(f"identifier {tid.rendered} matches {count} tasks")
        self.tid = tid
        self.count = count


class TaskIdAbsent(TaskIdRefusal):
    def __init__(self, count: int) -> None:
        super().__init__(
            f"{count} task(s) in this story carry no T# identifier — the story is not fully "
            "identified; write it through create_story/replace_story_body to mint ids before "
            "targeting a task by id"
        )
        self.count = count


class Completion(BaseModel):
    """How much of a task list is checked — a fact implied by the list's own contents."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    checked: int
    total: int

    @property
    def rendered(self) -> str:
        return f"{self.checked}/{self.total}"


def _completion(tasks: tuple[Task, ...]) -> Completion:
    return Completion(checked=sum(1 for t in tasks if t.checked), total=len(tasks))


class TaskList(RootModel[tuple[Task, ...]], frozen=True):
    root: tuple[Task, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _task_ids_are_unique(self) -> Self:
        ids = [t.tid.root for t in self.root if t.tid is not None]
        if len(set(ids)) != len(ids):
            raise ValueError("task identifiers must be unique within a story")
        return self

    @classmethod
    def minted(cls, tasks: tuple[Task, ...]) -> Self:
        """The trusted, fully-identified Tasks list: every task without a `T#` receives the next
        monotonic identifier (max(current) + 1, then increasing), every existing identifier kept
        unchanged. Ids only grow within the current set — a freed number is reused only if the
        highest task is removed and a new one added, the single bounded gap this construction leaves
        rather than persist an external high-water counter."""
        nxt = max((t.tid.root for t in tasks if t.tid is not None), default=0) + 1
        minted: list[Task] = []
        for task in tasks:
            if task.tid is None:
                minted.append(Task(checked=task.checked, tid=TaskId(nxt), text=task.text))
                nxt += 1
            else:
                minted.append(task)
        return cls(tuple(minted))

    @property
    def completion(self) -> Completion:
        return _completion(self.root)


class DefinitionOfDoneList(RootModel[tuple[Task, ...]], frozen=True):
    root: tuple[Task, ...] = Field(min_length=1)

    @property
    def completion(self) -> Completion:
        return _completion(self.root)


def _sectioned(body: str) -> dict[str, str]:
    parts = ("\n" + body).split("\n## ")
    return {p.splitlines()[0].strip(): "\n".join(p.splitlines()[1:]).strip() for p in parts[1:]}


def _fields(section: str, labels: tuple[str, ...]) -> dict[str, str]:
    """A labeled section's fields: each `**Label:**` marker owns the text up to the next marker.
    Values may span lines — a Choice can carry a real numbered list, not an inline (1)(2) chain."""
    found: list[tuple[int, str, int]] = []
    for label in labels:
        marker = f"**{label}:**"
        at = section.find(marker)
        if at < 0:
            raise ValueError(f"missing field '**{label}:**' — not a story section this tool can parse")
        found.append((at, label, len(marker)))
    found.sort()
    return {
        label: section[at + width : found[i + 1][0] if i + 1 < len(found) else len(section)].strip()
        for i, (at, label, width) in enumerate(found)
    }


_TASK_ID_RE = re.compile(r"^T(\d+)\s+—\s+(.*)$", re.DOTALL)


def _parse_task_line(line: str) -> Task:
    checked = line[3] == "x"
    body = line[6:].strip()
    m = _TASK_ID_RE.match(body)
    if m:
        return Task(checked=checked, tid=TaskId(int(m.group(1))), text=TaskText(m.group(2).strip()))
    return Task(checked=checked, text=TaskText(body))


def _tasks(section: str) -> tuple[Task, ...]:
    return tuple(
        _parse_task_line(line)
        for line in section.splitlines()
        if line.startswith("- [ ] ") or line.startswith("- [x] ")
    )


def _table_row_cells(line: str) -> list[str]:
    """The cells of one markdown table row, unescaping `\\|` back to a literal pipe."""
    inner = line.strip().strip("|")
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", inner)]


def _ceiling_table(maximum: str, chosen: str, constraint: str) -> str:
    def cell(s: str) -> str:
        return s.replace("|", "\\|").replace("\n", " ")

    return (
        "| Maximum | Chosen | Constraint |\n"
        "| --- | --- | --- |\n"
        f"| {cell(maximum)} | {cell(chosen)} | {cell(constraint)} |"
    )


def _parse_ceiling(section: str) -> dict[str, str]:
    """Ceiling fields from the table format; falls back to the bold-label format so a story not
    yet migrated to the table still parses."""
    rows = [ln for ln in section.splitlines() if ln.strip().startswith("|")]
    if len(rows) >= 3:
        cells = dict(zip(_table_row_cells(rows[0]), _table_row_cells(rows[2])))
        if {"Maximum", "Chosen", "Constraint"} <= set(cells):
            return {k: cells[k] for k in ("Maximum", "Chosen", "Constraint")}
    return _fields(section, ("Maximum", "Chosen", "Constraint"))


def _condemned_callout(path: str, reason: str, closure_test: str) -> str:
    body = f"**Path:** {path}\n\n**Reason:** {reason}\n\n**Closure test:** {closure_test}"
    quoted = "\n".join(f"> {ln}" if ln else ">" for ln in body.splitlines())
    return "> [!WARNING]\n" + quoted


def _dequote_callout(section: str) -> str:
    out: list[str] = []
    for ln in section.splitlines():
        s = ln[2:] if ln.startswith("> ") else (ln[1:] if ln.startswith(">") else ln)
        if s.strip().startswith("[!"):
            continue
        out.append(s)
    return "\n".join(out)


def _parse_condemned(section: str) -> dict[str, str]:
    """Condemned fields from inside the `[!WARNING]` callout; tolerant of a not-yet-wrapped body."""
    return _fields(_dequote_callout(section), ("Path", "Reason", "Closure test"))


def _unwrap_details(section: str) -> str:
    """The body inside a `<details>` wrap; tolerant of a section not yet wrapped."""
    s = section.strip()
    if not s.startswith("<details>"):
        return s
    lines = s.splitlines()[1:]
    if lines and lines[0].strip().startswith("<summary>"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "</details>":
        lines = lines[:-1]
    return "\n".join(lines).strip()


_EPIC_REF_RE = re.compile(r"#(\d+)")


def _parse_preamble(preamble: str) -> tuple[IssueNumber | None, LedeLine | None]:
    """Split a story's preamble into its parent-epic cross-link and its lede sentence. A line
    naming the parent epic (`**Epic:** #320`) yields the parent; remaining prose is the lede."""
    parent: IssueNumber | None = None
    lede_lines: list[str] = []
    for ln in preamble.splitlines():
        stripped = ln.strip()
        if stripped.startswith(("**Epic:**", "Epic:")):
            m = _EPIC_REF_RE.search(stripped)
            if m:
                parent = IssueNumber(int(m.group(1)))
                continue
        if stripped:
            lede_lines.append(stripped)
    lede = LedeLine(" ".join(lede_lines)) if lede_lines else None
    return parent, lede


class StoryBody(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    label: IssueLabel
    parent: IssueNumber | None = None
    lede: LedeLine | None = None
    description: StoryDescription
    sources: SourcesList
    condemned: Condemned
    ceiling: Ceiling
    engineering_choice: EngineeringChoice
    context: StoryContext
    tasks: TaskList
    definition_of_done: DefinitionOfDoneList

    @property
    def markdown(self) -> str:
        d = self.description
        c = self.condemned
        h = self.ceiling
        e = self.engineering_choice
        evidence = e.evidence.text.root if isinstance(e.evidence, EvidenceStated) else "None"
        preamble: list[str] = []
        if self.parent is not None:
            preamble += [f"**Epic:** #{self.parent.root}", ""]
        if self.lede is not None:
            preamble += [self.lede.root, ""]
        return "\n".join(
            [
                *preamble,
                "## Description",
                "",
                f"{d.actor.root},\nI want {d.want.root},\nso that {d.so_that.root}.",
                "",
                "## Sources",
                "",
                *[f"- {s.root}" for s in self.sources.root],
                "",
                "## Condemned",
                "",
                _condemned_callout(c.path.root, c.reason.root, c.closure_test.root),
                "",
                "## Ceiling",
                "",
                _ceiling_table(h.maximum.root, h.chosen.root, h.constraint.root),
                "",
                "## Engineering Choice",
                "",
                f"**Choice:** {e.choice.root}\n\n**Choice type:** {e.choice_type.root.value}\n\n"
                f"**Consequence:** {e.consequence.root}\n\n**Evidence needed:** {evidence}",
                "",
                "## Context",
                "",
                "<details>",
                "<summary>Execution context</summary>",
                "",
                self.context.root,
                "",
                "</details>",
                "",
                "## Tasks",
                "",
                *[t.markdown for t in self.tasks.root],
                "",
                "## Definition of Done",
                "",
                *[t.markdown for t in self.definition_of_done.root],
                "",
            ]
        )

    @classmethod
    def from_markdown(cls, label: IssueLabel, body: str) -> Self:
        sections = _sectioned(body)
        missing = [s for s in SECTION_ORDER if s not in sections]
        if missing:
            raise ValueError(f"story body missing section(s): {', '.join(missing)}")
        preamble = ("\n" + body).split("\n## ")[0].strip()
        parent, lede = _parse_preamble(preamble)
        # "<As … actor clause>,\nI want <want>,\nso that <so_that>." — the actor clause is carried
        # verbatim; this program does not own the grammar of "As a/an/the".
        raw = sections["Description"].strip()
        actor, _, rest = raw.partition(",\nI want ")
        want, _, so_that = rest.partition(",\nso that ")
        cond = _parse_condemned(sections["Condemned"])
        ceiling_lines = _parse_ceiling(sections["Ceiling"])
        choice_lines = _fields(
            sections["Engineering Choice"], ("Choice", "Choice type", "Consequence", "Evidence needed")
        )
        return cls(
            label=label,
            parent=parent,
            lede=lede,
            description=StoryDescription(actor=Actor(actor.strip()), want=Want(want.strip()), so_that=SoThat(so_that.strip().rstrip("."))),
            sources=SourcesList(tuple(
                SourceEntry(line[2:].strip())
                for line in sections["Sources"].splitlines()
                if line.startswith("- ")
            )),
            condemned=Condemned(
                path=CondemnedPath(cond["Path"]),
                reason=CondemnedReason(cond["Reason"]),
                closure_test=ClosureTest(cond["Closure test"]),
            ),
            ceiling=Ceiling(
                maximum=CeilingMaximum(ceiling_lines["Maximum"]),
                chosen=CeilingChosen(ceiling_lines["Chosen"]),
                constraint=CeilingConstraint(ceiling_lines["Constraint"]),
            ),
            engineering_choice=EngineeringChoice(
                choice=Choice(choice_lines["Choice"]),
                choice_type=ChoiceType(ChoiceTypeName(choice_lines["Choice type"])),
                consequence=Consequence(choice_lines["Consequence"]),
                evidence=(
                    EvidenceNotNeeded()
                    if choice_lines["Evidence needed"] == "None"
                    else EvidenceStated(text=EvidenceText(choice_lines["Evidence needed"]))
                ),
            ),
            context=StoryContext(_unwrap_details(sections["Context"])),
            tasks=TaskList(_tasks(sections["Tasks"])),
            definition_of_done=DefinitionOfDoneList(_tasks(sections["Definition of Done"])),
        )

    def with_task_id(self, tid: TaskId, checked: bool) -> Self:
        absent = sum(1 for t in self.tasks.root if t.tid is None)
        if absent:
            raise TaskIdAbsent(absent)
        hits = tuple(t for t in self.tasks.root if t.tid == tid)
        if len(hits) == 0:
            raise TaskIdNotFound(tid)
        if len(hits) > 1:
            raise TaskIdAmbiguous(tid, len(hits))
        target = hits[0]
        flipped = tuple(
            Task(checked=checked, tid=t.tid, text=t.text) if t is target else t
            for t in self.tasks.root
        )
        return self.model_copy(update={"tasks": TaskList(flipped)})
