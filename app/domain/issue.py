"""The foreign shape of a GitHub issue, lifted to exactly the seven facts a read of the board needs:
title, state, label, parent, sub-issues, body, comments. GitHub exposes far more; nothing here
claims what the intended function doesn't use. Each foreign lift is a named constructor on the type
it produces — the crossing happens here, once, at the type's own boundary, never in a separate
mapper file. Horizon is never one of these facts: it is column position, read from the project
board (`BoardEntry`/`BoardSurvey`), never from the issue itself."""

import json
from typing import Annotated, Literal, Self

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, RootModel

from app.domain.config import BoardTarget
from app.domain.gh import run
from app.domain.type import (
    GH_COLUMN,
    BoardColumn,
    BranchRef,
    ClosedReason,
    CommentText,
    IssueBodyText,
    IssueLabel,
    IssueNumber,
    IssueTitle,
    LabelName,
    Login,
    Timestamp,
)
from app.domain.value import ParentDeclared, ParentOmitted

ISSUE_FACTS = (
    "fragment IssueFacts on Issue { number title state stateReason closedAt body"
    " labels(first: 20) { totalCount nodes { name } }"
    " parent { number }"
    " subIssues(first: 50) { totalCount nodes { number title } }"
    " comments(first: 100) { totalCount nodes { author { login } body createdAt } }"
    " linkedBranches(first: 10) { totalCount nodes { ref { name } } } }"
)


def _complete(connection: dict, what: str, number: int) -> list[dict]:
    """A connection's nodes, provably all of them. A page that silently covers less than the total
    would let a read claim facts it never saw — truncation is a refusal, never a quiet subset."""
    nodes = connection["nodes"]
    if connection["totalCount"] > len(nodes):
        raise RuntimeError(
            f"#{number}: {what} truncated — {len(nodes)} of {connection['totalCount']} fetched; raise the page size"
        )
    return nodes


class IssueStateAxis(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class OpenIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    state: Literal[IssueStateAxis.OPEN] = IssueStateAxis.OPEN


class ClosedIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    state: Literal[IssueStateAxis.CLOSED] = IssueStateAxis.CLOSED
    reason: ClosedReason
    closed_at: Timestamp


IssueState = Annotated[OpenIssue | ClosedIssue, Field(discriminator="state")]


class Comment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    author: Login
    text: CommentText
    posted_at: Timestamp

    @property
    def rendered(self) -> str:
        return f"— {self.author.root} ({self.posted_at.root[:10]}): {self.text.root.rstrip()}"


class IssueSummary(BaseModel):
    """A parent or sub-issue reference: only what's rendered, never the whole issue."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    number: IssueNumber
    title: IssueTitle


def _observed_label(names: list[dict[str, str]]) -> IssueLabel | None:
    """The one classification label a card carries, if any of its labels is one of the five. Real
    board data includes cards predating that discipline, so absence is a real, not-exceptional case."""
    for entry in names:
        if entry["name"] in set(LabelName):
            return IssueLabel(LabelName(entry["name"]))
    return None


class IssueRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    number: IssueNumber
    title: IssueTitle
    state: OpenIssue | ClosedIssue = Field(discriminator="state")
    # Observed, not enforced: real board data includes issues predating the five-label discipline
    # (no label at all). Reading must not assume every card on the board went through this
    # program's own construction.
    label: IssueLabel | None
    parent: ParentDeclared | ParentOmitted = Field(discriminator="state")
    sub_issues: tuple[IssueSummary, ...]
    body: IssueBodyText
    comments: tuple[Comment, ...]
    linked_branches: tuple[BranchRef, ...]

    @classmethod
    def from_graphql(cls, node: dict) -> Self:
        """The one crossing from GitHub's GraphQL issue shape to the record. Every read — single,
        batch, or epic — lands here; there is no second parser to drift from this one."""
        number = node["number"]
        state = (
            ClosedIssue(
                reason=ClosedReason((node["stateReason"] or "COMPLETED").lower()),
                closed_at=Timestamp(node["closedAt"]),
            )
            if node["state"] == "CLOSED"
            else OpenIssue()
        )
        parent = ParentDeclared(epic=IssueNumber(node["parent"]["number"])) if node.get("parent") else ParentOmitted()
        return cls(
            number=IssueNumber(number),
            title=IssueTitle(node["title"]),
            state=state,
            label=_observed_label(_complete(node["labels"], "labels", number)),
            parent=parent,
            sub_issues=tuple(
                IssueSummary(number=IssueNumber(s["number"]), title=IssueTitle(s["title"]))
                for s in _complete(node["subIssues"], "sub-issues", number)
            ),
            body=IssueBodyText(node["body"]),
            comments=tuple(
                Comment(
                    author=Login(c["author"]["login"] if c["author"] else "ghost"),
                    text=CommentText(c["body"]),
                    posted_at=Timestamp(c["createdAt"]),
                )
                for c in _complete(node["comments"], "comments", number)
            ),
            linked_branches=tuple(
                BranchRef(b["ref"]["name"])
                for b in _complete(node["linkedBranches"], "linked branches", number)
                if b.get("ref")
            ),
        )

    @classmethod
    def fetch_many(cls, numbers: tuple[IssueNumber, ...], target: BoardTarget) -> tuple[Self, ...]:
        """Every requested issue in one crossing: aliased fields on one GraphQL query, however many
        numbers arrive. N issues never cost N subprocesses."""
        aliases = " ".join(f"i{n.root}: issue(number: {n.root}) {{ ...IssueFacts }}" for n in numbers)
        query = f"query($owner: String!, $name: String!) {{ repository(owner: $owner, name: $name) {{ {aliases} }} }} {ISSUE_FACTS}"
        raw = json.loads(run(
            "api", "graphql", "-F", f"owner={target.owner.root}", "-F", f"name={target.repo.root}",
            "-f", f"query={query}",
        ))
        repository = raw["data"]["repository"]
        missing = [f"#{n.root}" for n in numbers if repository[f"i{n.root}"] is None]
        if missing:
            raise ValueError(f"{', '.join(missing)}: no such issue in {target.owner.root}/{target.repo.root}")
        return tuple(cls.from_graphql(repository[f"i{n.root}"]) for n in numbers)

    @classmethod
    def fetch(cls, number: IssueNumber, target: BoardTarget) -> Self:
        return cls.fetch_many((number,), target)[0]

    @classmethod
    def node_id(cls, number: IssueNumber, target: BoardTarget) -> str:
        """The GraphQL node id, the one foreign key the sub-issue mutations need. Its own crossing,
        distinct from `fetch`: callers that only need the id should not pay for the whole record."""
        return json.loads(run(
            "issue", "view", str(number.root), "--repo", f"{target.owner.root}/{target.repo.root}", "--json", "id",
        ))["id"]

    @property
    def rendered(self) -> str:
        subs = " ".join(f"#{s.number.root}" for s in self.sub_issues)
        parent = f"#{self.parent.epic.root}" if isinstance(self.parent, ParentDeclared) else "none"
        label = self.label.root.value if self.label is not None else "none"
        branches = " branch=" + ",".join(b.root for b in self.linked_branches) if self.linked_branches else ""
        facts = f"state={self.state.state.value} label={label} parent={parent}{branches}"
        return "\n\n".join(
            part
            for part in (
                f"#{self.number.root} {self.title.root}\n{facts}" + (f"\nsubs: {subs}" if subs else ""),
                self.body.root.rstrip(),
                "\n".join(c.rendered for c in self.comments),
            )
            if part
        )


class BoardEntry(BaseModel):
    """One row of a board-column survey: enough to triage, not the whole issue."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    number: IssueNumber
    title: IssueTitle
    label: IssueLabel | None
    focus: bool

    @property
    def rendered(self) -> str:
        label = self.label.root.value if self.label is not None else "unlabeled"
        marker = " [focus]" if self.focus else ""
        return f"#{self.number.root} [{label}]{marker} {self.title.root}"


class BoardSurvey(RootModel[tuple[BoardEntry, ...]], frozen=True):
    """The result of querying one board column: every matching card, in the order `gh` returned
    them. Its own domain thing, not a bare list — a survey is itself a fact worth naming."""

    root: tuple[BoardEntry, ...]

    @classmethod
    def fetch(cls, column: BoardColumn, label: IssueLabel | None, focus_only: bool, target: BoardTarget) -> Self:
        reply = json.loads(run(
            "project", "item-list", str(target.project.root), "--owner", target.owner.root,
            "--format", "json", "--limit", "500",
        ))
        raw = reply["items"]
        if reply.get("totalCount", 0) > len(raw):
            raise RuntimeError(
                f"board survey truncated — {len(raw)} of {reply['totalCount']} cards fetched; "
                "the 500-card page no longer covers this board"
            )
        target_status = GH_COLUMN[column.root]
        entries: list[BoardEntry] = []
        for item in raw:
            content = item.get("content")
            if content is None or item.get("status") != target_status:
                continue
            item_labels = item.get("labels", [])
            has_focus = "focus" in item_labels
            if focus_only and not has_focus:
                continue
            item_label = next((n for n in item_labels if n in set(LabelName)), None)
            if label is not None and (item_label is None or LabelName(item_label) is not label.root):
                continue
            entries.append(BoardEntry(
                number=IssueNumber(content["number"]),
                title=IssueTitle(content["title"]),
                label=IssueLabel(LabelName(item_label)) if item_label is not None else None,
                focus=has_focus,
            ))
        return cls(tuple(entries))
