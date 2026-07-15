"""The atomic domain vocabulary: one frozen scalar per domain quantity, its constraint carried on
its own `Field`, never on a bare primitive. Each enum here is exactly the value-space a scalar wraps,
never used as a field's type directly."""

import re
from typing import Literal
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator

# ── Identity ──────────────────────────────────────────────────────────────────


class IssueNumber(RootModel[int], frozen=True):
    """A GitHub issue's number: the identity of any epic or story on the board."""

    root: int = Field(gt=0)


# ── Closed vocabularies ──────────────────────────────────────────────────────


class LabelName(StrEnum):
    FEATURE = "Feature"
    BUG = "Bug"
    PERFORMANCE = "Performance"
    SECURITY = "Security"
    DEMO = "Demo"


class IssueLabel(RootModel[LabelName], frozen=True):
    """The one classification chip an epic or story carries. Named `IssueLabel`, not `Label`: a
    board issue's closed five-value classification is a different thing from an ONTOK construct's
    free-text display label (`app.domain.know.ontok.Label`), and the two must never collide."""

    root: LabelName


class ChoiceTypeName(StrEnum):
    REPRESENTATION = "Representation"
    AUTHORITY_BOUNDARY = "Authority Boundary"
    EXECUTION_CURRENCY = "Execution Currency"
    CACHE_INVALIDATION = "Cache Invalidation"
    STORAGE_CONTRACT = "Storage Contract"
    ORDERING_INVARIANT = "Ordering Invariant"
    ADMISSION_PATH = "Admission Path"
    EVALUATOR_RULE = "Evaluator Rule"
    ALGORITHM = "Algorithm"
    BENCHMARK = "Benchmark"
    FAILURE_PATH = "Failure Path"
    EVIDENCE_BOUNDARY = "Evidence Boundary"


class ChoiceType(RootModel[ChoiceTypeName], frozen=True):
    """The axis an engineering choice sits on."""

    root: ChoiceTypeName


# ── Free text, each its own meaning ──────────────────────────────────────────


class EpicName(RootModel[str], frozen=True):
    """An epic's title: the value boundary it crosses."""

    root: str = Field(min_length=1)


class StoryName(RootModel[str], frozen=True):
    """A story's title: domain plus value-bearing mechanism."""

    root: str = Field(min_length=1)


class OutcomeDescription(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class Actor(RootModel[str], frozen=True):
    """The description's opening clause, verbatim — e.g. "As the repo operator". Carried whole:
    decomposing a natural-language clause the program doesn't own is how "As a As the ..." happens."""

    root: str = Field(min_length=1)


class SourceEntry(RootModel[str], frozen=True):
    """One Sources bullet, verbatim: the cited law or evidence line a story serves."""

    root: str = Field(min_length=1)


class CeilingMaximum(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class CeilingChosen(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class CeilingConstraint(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class Want(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class SoThat(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class CondemnedPath(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class CondemnedReason(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class ClosureTest(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class Choice(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class Consequence(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class EvidenceText(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class StoryContext(RootModel[str], frozen=True):
    """A story body's free-text Context section. Named `StoryContext`, not `Context`: distinct
    from ONTOK's `Context` kernel primitive (`app.domain.know.ontok.Context`, a structured scope
    a claim, state, relation, or rule is anchored in), which this is not."""

    root: str = Field(min_length=1)


class TaskText(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class AllowlistPath(RootModel[str], frozen=True):
    """One path or glob the executor may touch for a task — board state, not spawn gossip."""

    root: str = Field(min_length=1)


class SealCommand(RootModel[str], frozen=True):
    """The exact verification command a task must run — matched byte-for-byte at completion."""

    root: str = Field(min_length=1)


class TaskId(RootModel[int], frozen=True):
    """A task's append-only identity within its story's Tasks list: assigned once, never
    reused, never renumbered. `T3` renders and parses as the integer 3."""

    root: int = Field(ge=1)

    @property
    def rendered(self) -> str:
        return f"T{self.root}"


class LedeLine(RootModel[str], frozen=True):
    """One plain-language sentence at the top of a story or epic body: the human-narrative
    entry point, authored per issue, never generated by the migration."""

    root: str = Field(min_length=1)


class CommentText(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


_ILLEGAL_GIT_REF = re.compile(r"[ \t~^:?*\[\\\x00-\x1f]|\.\.|^[-/]|/$|//|@\{|\.lock$|^\.|\.$")


class BranchRef(RootModel[str], frozen=True):
    """The name of a git branch: a legal, injection-safe git ref. A name git would read as an option
    (leading ``-``) or that breaks git's ref grammar (whitespace, ``..``, any of ``~^:?*[\\``, a
    trailing ``/`` or ``.lock``, …) cannot be constructed, so it can never reach a git or gh argument
    as an injected flag or malformed ref."""

    root: str = Field(min_length=1)

    @field_validator("root")
    @classmethod
    def _legal_ref(cls, value: str) -> str:
        if _ILLEGAL_GIT_REF.search(value):
            raise ValueError(f"'{value}' is not a legal, injection-safe git branch name")
        return value


class CommitCount(RootModel[int], frozen=True):
    """A count of commits in a rev range — never negative."""

    root: int = Field(ge=0)


class Login(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class Timestamp(RootModel[str], frozen=True):
    """An ISO-8601 instant, GitHub's own encoding, carried whole."""

    root: str = Field(min_length=1)


class ClosedReason(RootModel[str], frozen=True):
    """GitHub's own closing-reason vocabulary (e.g. completed, not_planned), mirrored open."""

    root: str = Field(min_length=1)


class IssueTitle(RootModel[str], frozen=True):
    """An already-created issue's title, read back. A foreign mirror, not a construction input."""

    root: str = Field(min_length=1)


class IssueBodyText(RootModel[str], frozen=True):
    """An issue's raw markdown body, read back whole."""

    root: str = Field(min_length=1)


class ColumnAxis(StrEnum):
    """The board's single horizon-and-state axis: column position alone, in the board's real
    left-to-right order. Milestones are retired entirely — there is no second axis. `BACKLOG` is
    where every open card that isn't `IN_PROGRESS` rests unless an epic has been deliberately
    placed on `LATER`/`NEXT`/`NOW` to carry visible horizon; a story's own horizon is read off its
    parent epic, never carried on the story. Member order IS the column order `create_board`
    provisions."""

    BACKLOG = "backlog"
    NOW = "now"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    NEXT = "next"
    LATER = "later"
    DONE = "done"


class BoardColumn(RootModel[ColumnAxis], frozen=True):
    """The column being surveyed or reported. Distinct from `ColumnDestination`: querying "what's
    in Backlog" carries none of the proof a move into In Progress requires."""

    root: ColumnAxis


class ColumnName(RootModel[str], frozen=True):
    """A Status option's rendered name on GitHub — the string every board read and write keys on."""

    root: str = Field(min_length=1)


class OptionColorName(StrEnum):
    """GitHub's closed `ProjectV2SingleSelectFieldOptionColor` vocabulary."""

    GRAY = "GRAY"
    BLUE = "BLUE"
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ORANGE = "ORANGE"
    RED = "RED"
    PINK = "PINK"
    PURPLE = "PURPLE"


class OptionColor(RootModel[OptionColorName], frozen=True):
    """A Status option's dot color, proven a member of GitHub's closed color vocabulary."""

    root: OptionColorName


class ColumnDescription(RootModel[str], frozen=True):
    """The one-line meaning shown under a column's header."""

    root: str = Field(min_length=1)


class ColumnSpec(BaseModel):
    """One column's provisioned identity on GitHub: the Status option's name, dot color, and
    description. `GH_COLUMN`'s name view of this is what every read and write keys on; the full
    spec is what `create_board` authors. One table, so the recognizer and the constructor cannot
    drift."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: ColumnName
    color: OptionColor
    description: ColumnDescription


BOARD_COLUMNS: dict[ColumnAxis, ColumnSpec] = {
    ColumnAxis.BACKLOG: ColumnSpec(
        name=ColumnName("Backlog"),
        color=OptionColor(OptionColorName.GRAY),
        description=ColumnDescription("Open issues not In Progress; hidden working store."),
    ),
    ColumnAxis.NOW: ColumnSpec(
        name=ColumnName("Now"),
        color=OptionColor(OptionColorName.ORANGE),
        description=ColumnDescription("Epics for now; multi-epic at-a-glance status."),
    ),
    ColumnAxis.IN_PROGRESS: ColumnSpec(
        name=ColumnName("In Progress"),
        color=OptionColor(OptionColorName.YELLOW),
        description=ColumnDescription("Actively being built."),
    ),
    ColumnAxis.BLOCKED: ColumnSpec(
        name=ColumnName("Blocked"),
        color=OptionColor(OptionColorName.RED),
        description=ColumnDescription("Real named technical blocker (forcing function)."),
    ),
    ColumnAxis.NEXT: ColumnSpec(
        name=ColumnName("Next"),
        color=OptionColor(OptionColorName.PURPLE),
        description=ColumnDescription("Epics for next."),
    ),
    ColumnAxis.LATER: ColumnSpec(
        name=ColumnName("Later"),
        color=OptionColor(OptionColorName.BLUE),
        description=ColumnDescription("Epics for later; pull-forward to Now anytime."),
    ),
    ColumnAxis.DONE: ColumnSpec(
        name=ColumnName("Done"),
        color=OptionColor(OptionColorName.GREEN),
        description=ColumnDescription("Completed."),
    ),
}

GH_COLUMN: dict[ColumnAxis, str] = {axis: spec.name.root for axis, spec in BOARD_COLUMNS.items()}


class FocusLabel(RootModel[Literal["focus"]], frozen=True):
    """The one auxiliary label: marks the single card being actively worked. Not a classification
    — `LabelName` stays the closed five — so it is its own one-member value space."""

    root: Literal["focus"] = "focus"


class LabelColor(RootModel[str], frozen=True):
    """A repo label's color as six hex digits, no '#'."""

    root: str = Field(pattern=r"^[0-9A-Fa-f]{6}$")


class LabelDescription(RootModel[str], frozen=True):
    """A repo label's one-line description."""

    root: str = Field(min_length=1)


class LabelSpec(BaseModel):
    """One repo label `create_board` provisions: its name — a classification from the closed five,
    or the focus label — with color and description."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: IssueLabel | FocusLabel
    color: LabelColor
    description: LabelDescription


BOARD_LABELS: tuple[LabelSpec, ...] = (
    LabelSpec(name=IssueLabel(LabelName.FEATURE), color=LabelColor("1D76DB"), description=LabelDescription("New capability or invariant")),
    LabelSpec(name=IssueLabel(LabelName.BUG), color=LabelColor("D73A4A"), description=LabelDescription("Defect against a ruled behavior")),
    LabelSpec(name=IssueLabel(LabelName.PERFORMANCE), color=LabelColor("FBCA04"), description=LabelDescription("Measured performance work")),
    LabelSpec(name=IssueLabel(LabelName.SECURITY), color=LabelColor("B60205"), description=LabelDescription("Security boundary work")),
    LabelSpec(name=IssueLabel(LabelName.DEMO), color=LabelColor("0E8A16"), description=LabelDescription("Demonstration evidence")),
    LabelSpec(name=FocusLabel(), color=LabelColor("5319E7"), description=LabelDescription("The one card being actively worked")),
)


class BoardTitle(RootModel[str], frozen=True):
    """A new project board's title, as it will render on GitHub."""

    root: str = Field(min_length=1)


class ProjectTitle(RootModel[str], frozen=True):
    """An existing project's title, read back. A foreign mirror, not a construction input."""

    root: str = Field(min_length=1)


# ── Time: a constructed instant, domain-wide — not owned by any one consumer ──


class Instant(RootModel[datetime], frozen=True):
    """A point in time meant for comparison and interval math. Distinct from `Timestamp`: that
    scalar is GitHub's own ISO-8601 string carried whole, a foreign mirror never reconstructed;
    this is a real constructed value, shared by whatever domain needs to reason about time
    (currently `app.domain.value.Validity`, consumed by the ONTOK kernel's interval fields)."""

    root: datetime
