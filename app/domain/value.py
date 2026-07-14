"""Small frozen compositions of scalars, and the unions that carry a choice as a structure instead
of a nullable field or a runtime check."""

from typing import Annotated, Literal

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.domain.type import (
    Actor,
    BranchRef,
    Choice,
    ChoiceType,
    ClosureTest,
    ColumnAxis,
    CommentText,
    CondemnedPath,
    CondemnedReason,
    Consequence,
    EvidenceText,
    Instant,
    IssueNumber,
    IssueTitle,
    SoThat,
    Want,
)

# ── StoryDescription, Condemned: fixed small compositions ────────────────────


class StoryDescription(BaseModel):
    """A story's user-story description: actor, want, so-that. Named `StoryDescription`, not
    `Description`: distinct from an ONTOK construct's free-text description
    (`app.domain.know.ontok.Description`), which this structured triple is not."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    actor: Actor
    want: Want
    so_that: SoThat


class Condemned(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: CondemnedPath
    reason: CondemnedReason
    closure_test: ClosureTest


# ── EvidenceNeeded: "None" was never a value, it's a second state ────────────


class EvidenceAxis(StrEnum):
    STATED = "stated"
    NOT_NEEDED = "not_needed"


class EvidenceStated(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    state: Literal[EvidenceAxis.STATED] = EvidenceAxis.STATED
    text: EvidenceText


class EvidenceNotNeeded(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    state: Literal[EvidenceAxis.NOT_NEEDED] = EvidenceAxis.NOT_NEEDED


EvidenceNeeded = Annotated[EvidenceStated | EvidenceNotNeeded, Field(discriminator="state")]


class EngineeringChoice(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    choice: Choice
    choice_type: ChoiceType
    consequence: Consequence
    evidence: EvidenceStated | EvidenceNotNeeded = Field(discriminator="state")


# ── ParentEpic: omission is only ever a deliberate operator act ──────────────


class ParentAxis(StrEnum):
    DECLARED = "declared"
    OPERATOR_OMITTED = "operator_omitted"


class ParentDeclared(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    state: Literal[ParentAxis.DECLARED] = ParentAxis.DECLARED
    epic: IssueNumber


class ParentOmitted(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    state: Literal[ParentAxis.OPERATOR_OMITTED] = ParentAxis.OPERATOR_OMITTED


ParentEpic = Annotated[ParentDeclared | ParentOmitted, Field(discriminator="state")]


# ── ColumnDestination: entering In Progress carries its own proof ────────────


class ToBacklog(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    column: Literal[ColumnAxis.BACKLOG] = ColumnAxis.BACKLOG


class ToLater(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    column: Literal[ColumnAxis.LATER] = ColumnAxis.LATER


class ToNext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    column: Literal[ColumnAxis.NEXT] = ColumnAxis.NEXT


class ToNow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    column: Literal[ColumnAxis.NOW] = ColumnAxis.NOW


class ToInProgress(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    column: Literal[ColumnAxis.IN_PROGRESS] = ColumnAxis.IN_PROGRESS
    branch: BranchRef


class ToBlocked(BaseModel):
    """Entering Blocked carries its own proof, exactly as In Progress does: the named technical
    blocker. The move posts it as a comment — a card cannot become Blocked with nothing blocking it."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    column: Literal[ColumnAxis.BLOCKED] = ColumnAxis.BLOCKED
    blocker: CommentText


class ToDone(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    column: Literal[ColumnAxis.DONE] = ColumnAxis.DONE


ColumnDestination = Annotated[
    ToBacklog | ToLater | ToNext | ToNow | ToInProgress | ToBlocked | ToDone, Field(discriminator="column")
]


# ── Anchors: where a thing lands in an ordered list, as structure, never a magic index ──


class CardAnchorAxis(StrEnum):
    TOP = "top"
    AFTER_CARD = "after_card"


class ToTop(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    position: Literal[CardAnchorAxis.TOP] = CardAnchorAxis.TOP


class AfterCard(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    position: Literal[CardAnchorAxis.AFTER_CARD] = CardAnchorAxis.AFTER_CARD
    card: IssueNumber


CardAnchor = Annotated[ToTop | AfterCard, Field(discriminator="position")]
"""Where a card lands in the project's item order — the one axis the board model carries. The
project's order is a single list; a column view shows its slice of that list, so top of the list
is top of the card's column."""


class SiblingAnchorAxis(StrEnum):
    FIRST = "first"
    AFTER_SIBLING = "after_sibling"


class ToFirst(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    position: Literal[SiblingAnchorAxis.FIRST] = SiblingAnchorAxis.FIRST


class AfterSibling(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    position: Literal[SiblingAnchorAxis.AFTER_SIBLING] = SiblingAnchorAxis.AFTER_SIBLING
    sibling: IssueNumber


SiblingAnchor = Annotated[ToFirst | AfterSibling, Field(discriminator="position")]
"""Where a story lands in its epic's sub-issue list — the list whose order IS the epic's
execution order."""


# ── Deletion: destroying an issue names what the caller believes it is destroying ──


class Deletion(BaseModel):
    """One issue named for permanent deletion: its number plus the exact title the caller believes
    that number carries. A mismatch refuses the whole batch — deleting the wrong number becomes
    unrepresentable instead of irreversible."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    number: IssueNumber
    title: IssueTitle


# ── Validity: an interval's unboundedness is real shape, never a sentinel None ──


class ValidityAxis(StrEnum):
    BOUNDED = "bounded"
    OPEN_START = "open_start"
    OPEN_END = "open_end"
    UNBOUNDED = "unbounded"


class Bounded(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    axis: Literal[ValidityAxis.BOUNDED] = ValidityAxis.BOUNDED
    starts_at: Instant
    ends_at: Instant


class OpenStart(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    axis: Literal[ValidityAxis.OPEN_START] = ValidityAxis.OPEN_START
    ends_at: Instant


class OpenEnd(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    axis: Literal[ValidityAxis.OPEN_END] = ValidityAxis.OPEN_END
    starts_at: Instant


class Unbounded(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    axis: Literal[ValidityAxis.UNBOUNDED] = ValidityAxis.UNBOUNDED


Validity = Annotated[Bounded | OpenStart | OpenEnd | Unbounded, Field(discriminator="axis")]
