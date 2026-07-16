"""The board's MCP surface: one route per meaning. No consistency model exists — nothing here is
held live between calls — so each route performs its one causal crossing directly. A foreign-data
lift that constructs a typed value lives on that type (`IssueRecord.fetch`); a causal mutation
shared by more than one route lives here as a private helper."""

import json
from collections.abc import Callable
from functools import cache
from typing import Any

from app.api import mcp
from fnmatch import fnmatch

from app.domain.config import BoardTarget, ProjectNumber, RepoName, RepoOwner
from app.domain.config import SETTINGS
from app.domain.target import configured_target
from app.domain.epic import EpicBody
from app.domain import git
from app.domain.gh import graphql, run
from app.domain.issue import BoardEntry, BoardSurvey, ClosedIssue, IssueRecord, OpenIssue
from app.domain.story import StoryBody, Task, TaskList
from app.domain.type import (
    BOARD_COLUMNS,
    BOARD_LABELS,
    GH_COLUMN,
    BoardColumn,
    BoardTitle,
    ColumnAxis,
    CommitCount,
    BranchRef,
    CommentText,
    EpicName,
    IssueLabel,
    IssueNumber,
    IssueTitle,
    LabelName,
    CheckCommand,
    StoryName,
    TaskId,
)
from app.domain.value import (
    AfterCard,
    AfterSibling,
    Allowlist,
    CardAnchor,
    ColumnDestination,
    Deletion,
    ParentDeclared,
    ParentEpic,
    SiblingAnchor,
    ToBacklog,
    ToBlocked,
    ToDone,
    ToFirst,
    ToInProgress,
    ToLater,
    ToNext,
    ToNow,
)

# ── The board a call acts on ─────────────────────────────────────────────────


@cache
def _default_board() -> BoardTarget:
    """The configured/derived default, resolved once on first need — never at import. A repo
    with no derivable board still boots the server; the refusal surfaces on the first call that
    actually needs a target, and `create_board` (which needs none) stays reachable to fix it."""
    return configured_target(SETTINGS)


def _board(target: BoardTarget | None) -> BoardTarget:
    return target if target is not None else _default_board()


# ── Private helpers: causal mutations shared by more than one route ──────────


def _create_issue(title: str, body_md: str, label: IssueLabel, target: BoardTarget) -> IssueNumber:
    url = run(
        "issue", "create", "--repo", f"{target.owner.root}/{target.repo.root}", "--title", title,
        "--label", label.root.value, "--body-file", "-", stdin=body_md,
    ).strip()
    return IssueNumber(int(url.rsplit("/", 1)[1]))


def _edit_body(number: IssueNumber, body_md: str, target: BoardTarget) -> None:
    run("issue", "edit", str(number.root), "--repo", f"{target.owner.root}/{target.repo.root}", "--body-file", "-", stdin=body_md)


def _add_comment(number: IssueNumber, text: CommentText, target: BoardTarget) -> None:
    run("issue", "comment", str(number.root), "--repo", f"{target.owner.root}/{target.repo.root}", "--body", text.root)


def _set_label(number: IssueNumber, label: IssueLabel, target: BoardTarget) -> None:
    others = ",".join(m.value for m in LabelName if m is not label.root)
    run("issue", "edit", str(number.root), "--repo", f"{target.owner.root}/{target.repo.root}",
        "--add-label", label.root.value, "--remove-label", others)


_SUB_ISSUE_MUTATION = "mutation($p:ID!,$c:ID!){{{op}(input:{{issueId:$p,subIssueId:$c}}){{issue{{number}}}}}}"


def _attach(parent: IssueNumber, child: IssueNumber, target: BoardTarget) -> None:
    run("api", "graphql", "-F", f"p={IssueRecord.node_id(parent, target)}", "-F", f"c={IssueRecord.node_id(child, target)}",
        "-f", f"query={_SUB_ISSUE_MUTATION.format(op='addSubIssue')}")


def _detach(parent: IssueNumber, child: IssueNumber, target: BoardTarget) -> None:
    run("api", "graphql", "-F", f"p={IssueRecord.node_id(parent, target)}", "-F", f"c={IssueRecord.node_id(child, target)}",
        "-f", f"query={_SUB_ISSUE_MUTATION.format(op='removeSubIssue')}")


def _card_id(number: IssueNumber, target: BoardTarget) -> str | None:
    reply = json.loads(run("project", "item-list", str(target.project.root), "--owner", target.owner.root, "--format", "json", "--limit", "500"))
    if reply.get("totalCount", 0) > len(reply["items"]):
        raise RuntimeError(
            f"card lookup for #{number.root} truncated — {len(reply['items'])} of {reply['totalCount']} cards "
            "fetched; the 500-card page no longer covers this board"
        )
    ids = [i["id"] for i in reply["items"] if i.get("content", {}).get("number") == number.root]
    return ids[0] if ids else None


def _place_card(number: IssueNumber, target: BoardTarget) -> str:
    reply = json.loads(run("project", "item-add", str(target.project.root), "--owner", target.owner.root, "--format", "json",
                            "--url", f"https://github.com/{target.owner.root}/{target.repo.root}/issues/{number.root}"))
    return reply["id"]


_PROJECT_STATUS_QUERY = (
    'query($owner: String!, $number: Int!) { repositoryOwner(login: $owner) {'
    ' ... on Organization { projectV2(number: $number) { id field(name: "Status") { ... on ProjectV2SingleSelectField { id options { id name } } } } }'
    ' ... on User { projectV2(number: $number) { id field(name: "Status") { ... on ProjectV2SingleSelectField { id options { id name } } } } } } }'
)


def _status_field(target: BoardTarget) -> tuple[str, str, dict[str, str]]:
    """The project id, Status field id, and option-name→id map, in one crossing. Schema drift —
    a missing project, field, or option — refuses by name instead of dying in an anonymous next()."""
    data = graphql(_PROJECT_STATUS_QUERY, owner=target.owner.root, number=str(target.project.root))
    project = (data["repositoryOwner"] or {}).get("projectV2")
    if project is None:
        raise RuntimeError(f"project {target.project.root} not found under {target.owner.root}")
    field = project.get("field")
    if field is None or "options" not in field:
        raise RuntimeError("project has no 'Status' single-select field — the board schema drifted")
    return project["id"], field["id"], {o["name"]: o["id"] for o in field["options"]}


def _set_column(number: IssueNumber, destination: ColumnDestination, target: BoardTarget, *, creating: bool = False) -> None:
    item_id = _place_card(number, target) if creating else _card_id(number, target)
    if item_id is None:
        raise RuntimeError(f"#{number.root} has no card on the board — surface the drift, don't repair it")
    project_id, field_id, options = _status_field(target)
    option_id = options.get(GH_COLUMN[destination.column])
    if option_id is None:
        raise RuntimeError(
            f"Status has no '{GH_COLUMN[destination.column]}' option — the board schema drifted "
            f"(present: {', '.join(options)})"
        )
    run("project", "item-edit", "--id", item_id, "--project-id", project_id,
        "--field-id", field_id, "--single-select-option-id", option_id)
    if isinstance(destination, ToBlocked):
        _add_comment(number, CommentText(f"Blocked: {destination.blocker.root}"), target)
    if isinstance(destination, ToInProgress):
        run("issue", "edit", str(number.root), "--repo", f"{target.owner.root}/{target.repo.root}",
            "--add-label", "focus", "--add-assignee", "@me")
    else:
        run("issue", "edit", str(number.root), "--repo", f"{target.owner.root}/{target.repo.root}", "--remove-label", "focus")


def _linked_branches(number: IssueNumber, target: BoardTarget) -> tuple[BranchRef, ...]:
    data = graphql(
        "query($n: Int!, $owner: String!, $name: String!) { repository(owner: $owner, name: $name) "
        "{ issue(number: $n) { linkedBranches(first: 10) { nodes { ref { name } } } } } }",
        n=str(number.root), owner=target.owner.root, name=target.repo.root,
    )
    nodes = data["repository"]["issue"]["linkedBranches"]["nodes"]
    return tuple(BranchRef(n["ref"]["name"]) for n in nodes if n.get("ref"))


def _delete_issue(number: IssueNumber, target: BoardTarget) -> None:
    run("issue", "delete", str(number.root), "--repo", f"{target.owner.root}/{target.repo.root}", "--yes")


def _close_issue(number: IssueNumber, target: BoardTarget) -> None:
    run("issue", "close", str(number.root), "--repo", f"{target.owner.root}/{target.repo.root}")


def _rename_issue(number: IssueNumber, name: StoryName, target: BoardTarget) -> None:
    run("issue", "edit", str(number.root), "--repo", f"{target.owner.root}/{target.repo.root}", "--title", name.root)


def _current_story(number: IssueNumber, target: BoardTarget) -> StoryBody:
    record = IssueRecord.fetch(number, target)
    if record.label is None:
        raise ValueError(f"#{number.root} carries no classification label — not a story this tool can parse")
    return StoryBody.from_markdown(record.label, record.body.root)


# ── Routes ─────────────────────────────────────────────────────────────────


_OWNER_REPO_QUERY = (
    "query($owner: String!, $name: String!) { repositoryOwner(login: $owner) { id } "
    "repository(owner: $owner, name: $name) { id } }"
)
_PROJECT_CREATE = (
    "mutation($o: ID!, $t: String!) { createProjectV2(input: {ownerId: $o, title: $t}) "
    "{ projectV2 { id number } } }"
)
_STATUS_FIELD_BY_PROJECT = (
    'query($p: ID!) { node(id: $p) { ... on ProjectV2 { field(name: "Status") '
    "{ ... on ProjectV2SingleSelectField { id } } } } }"
)
_LINK_REPO = (
    "mutation($p: ID!, $r: ID!) { linkProjectV2ToRepository(input: {projectId: $p, repositoryId: $r}) "
    "{ repository { id } } }"
)


def _status_options_mutation() -> str:
    """The Status-field rewrite, its options inlined from `BOARD_COLUMNS` — the one schema table —
    in `ColumnAxis` order. Inlined rather than passed as a variable because option colors are a
    GraphQL enum, and every inlined value is one of this program's own typed constants."""
    options = ", ".join(
        f'{{name: "{spec.name.root}", color: {spec.color.root.value}, description: "{spec.description.root}"}}'
        for spec in BOARD_COLUMNS.values()
    )
    return (
        f"mutation($f: ID!) {{ updateProjectV2Field(input: {{fieldId: $f, singleSelectOptions: [{options}]}}) "
        "{ projectV2Field { ... on ProjectV2SingleSelectField { id } } } }"
    )


@mcp.tool(
    name="create_board",
    description="Provision a new board carrying the plan schema — the same one table the "
    "readers and gates enforce, so the constructor and recognizers cannot drift: the seven Status "
    "columns in order (Backlog, Now, In Progress, Blocked, Next, Later, Done) with their colors "
    "and descriptions, the five classification labels plus focus in the target repo (created only "
    "where missing — an existing label is never altered), and the project linked to the repo. "
    "Creates a brand-new GitHub project every call and verifies the result with the same schema "
    "read every other tool trusts. Returns the PLAN_BOARD_* triple to configure.",
)
def create_board(title: BoardTitle, owner: RepoOwner, repo: RepoName) -> str:
    ids = graphql(_OWNER_REPO_QUERY, owner=owner.root, name=repo.root)
    if ids.get("repositoryOwner") is None:
        raise RuntimeError(f"no such owner: {owner.root}")
    if ids.get("repository") is None:
        raise RuntimeError(f"no such repository: {owner.root}/{repo.root}")
    created = graphql(_PROJECT_CREATE, o=ids["repositoryOwner"]["id"], t=title.root)["createProjectV2"]["projectV2"]
    project_id, number = created["id"], ProjectNumber(created["number"])
    field = graphql(_STATUS_FIELD_BY_PROJECT, p=project_id)["node"]["field"]
    if field is None or "id" not in field:
        raise RuntimeError("new project has no 'Status' single-select field — GitHub's default schema changed")
    graphql(_status_options_mutation(), f=field["id"])
    graphql(_LINK_REPO, p=project_id, r=ids["repository"]["id"])
    existing = {entry["name"].casefold() for entry in json.loads(run("label", "list", "--repo", f"{owner.root}/{repo.root}", "--json", "name"))}
    for spec in BOARD_LABELS:
        if str(spec.name.root).casefold() not in existing:
            run(
                "label", "create", str(spec.name.root), "--repo", f"{owner.root}/{repo.root}",
                "--color", spec.color.root, "--description", spec.description.root,
            )
    target = BoardTarget(owner=owner, repo=repo, project=number)
    _status_field(target)  # verify with the recognizer every other tool trusts
    return (
        f"create_board: {owner.root}/{repo.root} project {number.root} ready — configure "
        f"PLAN_BOARD_OWNER={owner.root} PLAN_BOARD_REPO={repo.root} PLAN_BOARD_PROJECT={number.root}"
    )


@mcp.tool(
    name="create_epic",
    description="Create a new epic issue: sets its label and outcome-description body, and places "
    "its card in the given column — typically Later, Next, or Now, the epic's visible horizon. Use "
    "when starting a new epic-level body of work on the board. `target` defaults to the "
    "configured board; pass an explicit owner/repo/project to act on a different one (e.g. a "
    "disposable test board).",
)
def create_epic(
    name: EpicName, body: EpicBody, column: ColumnDestination, target: BoardTarget | None = None,
) -> str:
    target = _board(target)
    number = _create_issue(name.root, body.markdown, body.label, target)
    _set_column(number, column, target, creating=True)
    return f"create_epic: #{number.root}"


@mcp.tool(
    name="replace_epic_outcome",
    description="Replace an epic's Outcome Description body and label. Use to rewrite what value "
    "boundary an epic crosses; body and label chip must agree, so both are given together.",
)
def replace_epic_outcome(number: IssueNumber, body: EpicBody, target: BoardTarget | None = None) -> str:
    target = _board(target)
    _edit_body(number, body.markdown, target)
    _set_label(number, body.label, target)
    return f"replace_epic_outcome: #{number.root}"


@mcp.tool(
    name="comment_on_epic",
    description="Append one comment to an epic issue. Use for status notes that don't change the "
    "epic's own contract.",
)
def comment_on_epic(number: IssueNumber, comment: CommentText, target: BoardTarget | None = None) -> str:
    target = _board(target)
    _add_comment(number, comment, target)
    return f"comment_on_epic: #{number.root}"


@mcp.tool(
    name="create_story",
    description="Create a new story issue with its full contract (description, condemned path, "
    "engineering choice, tasks, definition of done), attach it to a parent epic unless omission is "
    "an explicit operator decision, and place its card. A story's own horizon is read off its "
    "parent epic's column, not carried on the story — new stories normally start in Backlog "
    "(ToBacklog) unless work begins immediately. Use when starting a new story.",
)
def create_story(
    name: StoryName, parent: ParentEpic, column: ColumnDestination, body: StoryBody,
    target: BoardTarget | None = None,
) -> str:
    target = _board(target)
    body = body.model_copy(update={"tasks": TaskList.minted(body.tasks.root)})
    number = _create_issue(name.root, body.markdown, body.label, target)
    if isinstance(parent, ParentDeclared):
        _attach(parent.epic, number, target)
    _set_column(number, column, target, creating=True)
    return f"create_story: #{number.root}"


def _path_in_allowlist(path: str, allowlist: Allowlist) -> bool:
    for item in allowlist.root:
        pat = item.root
        if any(ch in pat for ch in "*?["):
            if fnmatch(path, pat):
                return True
            continue
        if path == pat or path.startswith(pat.rstrip("/") + "/"):
            return True
    return False


@mcp.tool(
    name="check_story_task",
    description="JUDGE ONLY after verify_task_completion PASS — flip one Tasks T# checkbox. "
    "`task_id` is N in TN. Never from demolition/development-task/parent shortcut. "
    "DoD is check_final_qa, not this tool.",
)
def check_story_task(number: IssueNumber, task_id: TaskId, target: BoardTarget | None = None) -> str:
    target = _board(target)
    story = _current_story(number, target)
    _edit_body(number, story.with_task_id(task_id, checked=True).markdown, target)
    return f"check_story_task: #{number.root} {task_id.rendered}"


@mcp.tool(
    name="check_final_qa",
    description="PARENT ONLY after every T# is checked AND after posting a FINAL QA comment "
    "(VALUE / CONDEMNED / CHOICE / SOURCES). Flips the single Final QA DoD box. Refuses while "
    "Tasks incomplete. Not judge/demolition/task. No worktrees, Witness, or CI-in-Plan.",
)
def check_final_qa(number: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    story = _current_story(number, target)
    tasks = story.tasks.completion
    if tasks.checked != tasks.total:
        raise ValueError(
            f"#{number.root} Tasks incomplete ({tasks.rendered}) — finish every T# via the judge "
            "before Final QA"
        )
    updated = story.with_dod_all_checked(True)
    _edit_body(number, updated.markdown, target)
    return (
        f"check_final_qa: #{number.root} definition_of_done "
        f"{updated.definition_of_done.completion.rendered}"
    )


@mcp.tool(
    name="verify_task_completion",
    description="JUDGE ONLY before check_story_task. Supply check_command from read_task_slice "
    "(board Check), never from agent testimony. Passes only if Check matches board and dirty "
    "paths vs HEAD are non-empty and ⊆ Allowlist. Optional base_rev = committed range. "
    "Task agents never call this or run git.",
)
def verify_task_completion(
    number: IssueNumber,
    task_id: TaskId,
    check_command: CheckCommand,
    base_rev: str | None = None,
    target: BoardTarget | None = None,
) -> str:
    target = _board(target)
    story = _current_story(number, target)
    task = story.task_by_id(task_id)
    if task.allowlist is None:
        raise ValueError(
            f"{task_id.rendered} has no Allowlist on the board — rewrite the task with "
            "`**Allowlist:**` paths before verifying"
        )
    if task.check is None:
        raise ValueError(
            f"{task_id.rendered} has no `**Check:**` on the task — add the check command there "
            "(not on Definition of Done)"
        )
    board_check = task.check
    if check_command.root != board_check.root:
        raise ValueError(
            f"VALIDATION narrowed or drifted — submitted `{check_command.root}` != board "
            f"`{board_check.root}`"
        )
    if base_rev is not None:
        base = base_rev
        paths = git.changed_paths(base)
        meter = f"commits {base}...HEAD"
    else:
        base = "HEAD+worktree"
        paths = git.dirty_paths()
        meter = "dirty worktree vs HEAD"
    if not paths:
        raise ValueError(
            f"TREE DIFF empty ({meter}, base={base}) — no paths changed; empty diff is not completion"
        )
    off = tuple(p for p in paths if not _path_in_allowlist(p, task.allowlist))
    if off:
        raise ValueError(
            f"TREE DIFF outside Allowlist — off-list: {', '.join(off)}; "
            f"allowlist: {', '.join(a.root for a in task.allowlist.root)}; "
            f"base={base} ({meter}). Foreign porcelain: restore or escalate — never stash"
        )
    return (
        f"verify_task_completion: PASS #{number.root} {task_id.rendered}\n"
        f"check: {board_check.root}\n"
        f"base: {base}\n"
        f"meter: {meter}\n"
        f"paths ({len(paths)}):\n"
        + "\n".join(f"- {p}" for p in paths)
    )


@mcp.tool(
    name="read_task_slice",
    description="PARENT and JUDGE. One T#: task text, Allowlist, Check, Condemned, Context. "
    "Judge takes Check from here for verify. Executor edits Allowlist only — no shell or git. "
    "Parent runs Check after edits, before judge.",
)
def read_task_slice(number: IssueNumber, task_id: TaskId, target: BoardTarget | None = None) -> str:
    target = _board(target)
    story = _current_story(number, target)
    task = story.task_by_id(task_id)
    check_cmd = task.check.root if task.check is not None else "(none — add Check on the task)"
    allow = (
        ", ".join(f"`{p.root}`" for p in task.allowlist.root)
        if task.allowlist is not None
        else "(none — add Allowlist)"
    )
    c = story.condemned
    return "\n".join(
        [
            f"read_task_slice: #{number.root} {task_id.rendered}",
            "ROLE: development-task edits ALLOWLIST only — parent runs CHECK; judge verifies",
            "",
            f"TASK: {task.markdown}",
            f"ALLOWLIST: {allow}",
            f"CHECK (parent runs): `{check_cmd}`",
            "",
            "CONDEMNED:",
            f"- Path: {c.path.root}",
            f"- Reason: {c.reason.root}",
            f"- Closure test: {c.closure_test.root}",
            "",
            "CONTEXT:",
            story.context.root,
        ]
    )


@mcp.tool(
    name="uncheck_story_task",
    description="Flip the task with the given T# identifier back to unchecked. `task_id` is the "
    "integer N of the task's `TN` identifier.",
)
def uncheck_story_task(number: IssueNumber, task_id: TaskId, target: BoardTarget | None = None) -> str:
    target = _board(target)
    story = _current_story(number, target)
    _edit_body(number, story.with_task_id(task_id, checked=False).markdown, target)
    return f"uncheck_story_task: #{number.root} {task_id.rendered}"


@mcp.tool(
    name="comment_on_story",
    description="Append one comment to a story issue.",
)
def comment_on_story(number: IssueNumber, comment: CommentText, target: BoardTarget | None = None) -> str:
    target = _board(target)
    _add_comment(number, comment, target)
    return f"comment_on_story: #{number.root}"


@mcp.tool(
    name="reparent_story",
    description="Reparent a story to a different epic: detaches it from its current parent, if any, "
    "and attaches it to the new one.",
)
def reparent_story(number: IssueNumber, epic: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    current = IssueRecord.fetch(number, target).parent
    if isinstance(current, ParentDeclared):
        _detach(current.epic, number, target)
    _attach(epic, number, target)
    return f"reparent_story: #{number.root}"


@mcp.tool(
    name="reclassify_story",
    description="Change a story's label to one of the five classes.",
)
def reclassify_story(number: IssueNumber, label: IssueLabel, target: BoardTarget | None = None) -> str:
    target = _board(target)
    _set_label(number, label, target)
    return f"reclassify_story: #{number.root}"


@mcp.tool(
    name="replace_story_body",
    description="Rewrite a story's whole contract: label and every body section. Use when the "
    "story's shape itself has changed, not for a single-field edit.",
)
def replace_story_body(number: IssueNumber, body: StoryBody, target: BoardTarget | None = None) -> str:
    target = _board(target)
    body = body.model_copy(update={"tasks": TaskList.minted(body.tasks.root)})
    _edit_body(number, body.markdown, target)
    _set_label(number, body.label, target)
    return f"replace_story_body: #{number.root}"


@mcp.tool(
    name="move_to_backlog",
    description="Move any card — epic or story — to Backlog and remove the focus label if present. "
    "Backlog is hidden: the resting place for everything open that isn't actively In Progress and "
    "isn't an epic deliberately carrying visible horizon on Later/Next/Now.",
)
def move_to_backlog(number: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    _set_column(number, ToBacklog(), target)
    return f"move_to_backlog: #{number.root}"


@mcp.tool(
    name="move_to_later",
    description="Move any card — normally an epic — to Later, the farthest visible horizon. "
    "Pulling an epic forward is a drag: move_to_next, then move_to_now.",
)
def move_to_later(number: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    _set_column(number, ToLater(), target)
    return f"move_to_later: #{number.root}"


@mcp.tool(
    name="move_to_next",
    description="Move any card — normally an epic — to Next, the middle visible horizon.",
)
def move_to_next(number: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    _set_column(number, ToNext(), target)
    return f"move_to_next: #{number.root}"


@mcp.tool(
    name="move_to_now",
    description="Move any card — normally an epic — to Now, the nearest visible horizon: the work "
    "queued to start when the current epic finishes.",
)
def move_to_now(number: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    _set_column(number, ToNow(), target)
    return f"move_to_now: #{number.root}"


@mcp.tool(
    name="move_to_in_progress",
    description="Move a story to In Progress, add the focus label, and assign the operating "
    "account (@me). In Progress is stories only — refuses epics (a started epic lives in Now; "
    "start_epic). A story rides its parent epic's branch and this refuses unless that branch "
    "exists (start_epic creates it).",
)
def move_to_in_progress(number: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    record = IssueRecord.fetch(number, target)
    if _is_epic(record):
        raise ValueError(
            f"#{number.root} is an epic — In Progress is stories only; a started epic lives in Now (start_epic)"
        )
    branch_source = record.parent.epic if isinstance(record.parent, ParentDeclared) else number
    branches = _linked_branches(branch_source, target)
    if not branches:
        where = f"parent epic #{branch_source.root}" if branch_source.root != number.root else "this epic"
        raise ValueError(
            f"#{number.root} has no epic branch ({where}) — focus rides the epic branch. "
            f"Start the epic first (start_epic)."
        )
    _set_column(number, ToInProgress(branch=branches[0]), target)
    return f"move_to_in_progress: #{number.root} on {branches[0].root}"


# ── Branch-per-epic lifecycle gates ──────────────────────────────────────────
#
# A start or a finish is a sequence of deterministic checks — each reads one git
# or board fact and compares it to a fixed expected value. The first failed
# check refuses with a typed variant and no mutation runs; only an all-pass
# reaches the branch and board writes. There is no judgment here, only
# comparison.


class GateRefusal(Exception):
    """A start_epic/start_story/finish_epic gate precondition that is not met — a typed, branchable
    refusal. Each concrete subclass names exactly one failed check."""


class DirtyWorkingTree(GateRefusal):
    def __init__(self) -> None:
        super().__init__(
            "working tree or index is not clean — commit allowlisted work, restore foreign paths, "
            "or escalate to the operator; never stash to pass this gate"
        )


class NotOnMain(GateRefusal):
    def __init__(self, on: BranchRef | None) -> None:
        where = f"'{on.root}'" if on is not None else "a detached HEAD"
        super().__init__(f"current branch is {where}, not 'main' — an epic starts from main")
        self.on = on


class MainBehindRemote(GateRefusal):
    def __init__(self, behind: CommitCount) -> None:
        super().__init__(f"main is {behind.root} commit(s) behind origin/main — pull before starting")
        self.behind = behind


class BranchAlreadyExists(GateRefusal):
    def __init__(self, name: BranchRef) -> None:
        super().__init__(f"branch '{name.root}' already exists locally or on origin — choose an unused name")
        self.name = name


class NotAnEpicWithStories(GateRefusal):
    def __init__(self, number: IssueNumber) -> None:
        super().__init__(f"#{number.root} is not an open epic with at least one story")
        self.number = number


class EpicAlreadyStarted(GateRefusal):
    def __init__(self, number: IssueNumber) -> None:
        super().__init__(f"epic #{number.root} already has a linked branch — it is already started")
        self.number = number


class PriorEpicUnfinished(GateRefusal):
    def __init__(self, branch: BranchRef) -> None:
        super().__init__(f"branch '{branch.root}' has commits not merged into main — a prior epic's work is still in flight; merge or delete it first")
        self.branch = branch


class StoryHasNoActiveEpic(GateRefusal):
    def __init__(self, number: IssueNumber) -> None:
        super().__init__(f"#{number.root} has no parent epic in Now with a linked branch (start_epic starts one)")
        self.number = number


class NotOnEpicBranch(GateRefusal):
    def __init__(self, on: BranchRef | None, expected: BranchRef) -> None:
        where = f"'{on.root}'" if on is not None else "a detached HEAD"
        super().__init__(f"HEAD is {where}, not the epic branch '{expected.root}' — check it out first")
        self.on = on
        self.expected = expected


class OperationInProgress(GateRefusal):
    def __init__(self) -> None:
        super().__init__("a merge, rebase, or cherry-pick is in progress — finish or abort it first")


class SiblingStoryInProgress(GateRefusal):
    def __init__(self, number: IssueNumber) -> None:
        super().__init__(f"story #{number.root} in this epic is already In Progress — one story at a time")
        self.number = number


class NotNextStory(GateRefusal):
    def __init__(self, number: IssueNumber, expected: IssueNumber | None) -> None:
        exp = f"#{expected.root}" if expected is not None else "none (every story is done)"
        super().__init__(f"#{number.root} is not the next unstarted story in sub-issue order — next is {exp}")
        self.number = number
        self.expected = expected


class PrecedingStoryIncomplete(GateRefusal):
    def __init__(self, number: IssueNumber) -> None:
        super().__init__(f"the preceding story #{number.root} is not Done with every Task and Definition-of-Done box checked")
        self.number = number


class EpicBranchDiverged(GateRefusal):
    def __init__(self, branch: BranchRef) -> None:
        super().__init__(f"epic branch '{branch.root}' has diverged from origin — reconcile before starting the next story")
        self.branch = branch


class NoWorkOnEpicBranch(GateRefusal):
    def __init__(self, branch: BranchRef) -> None:
        super().__init__(f"epic branch '{branch.root}' has no commit since the preceding story started, but that story is marked done — its work is missing")
        self.branch = branch


class EpicNotActive(GateRefusal):
    def __init__(self, number: IssueNumber) -> None:
        super().__init__(f"epic #{number.root} is not in Now on the board — only the active epic (in Now with a linked branch) can finish")
        self.number = number


class EpicBranchMissing(GateRefusal):
    def __init__(self, number: IssueNumber) -> None:
        super().__init__(f"epic #{number.root} has no linked branch — nothing records where its work landed")
        self.number = number


class StoryNotComplete(GateRefusal):
    def __init__(self, number: IssueNumber) -> None:
        super().__init__(f"story #{number.root} is not Done with every Task and Definition-of-Done box checked")
        self.number = number


class EpicBranchUnmerged(GateRefusal):
    def __init__(self, branch: BranchRef, ahead: CommitCount) -> None:
        super().__init__(f"epic branch '{branch.root}' carries {ahead.root} commit(s) not merged into main — merge before finishing")
        self.branch = branch
        self.ahead = ahead


_COLUMN_BY_GH: dict[str, ColumnAxis] = {gh: axis for axis, gh in GH_COLUMN.items()}
_IN_PROGRESS = BoardColumn(ColumnAxis.IN_PROGRESS)
_NOW = BoardColumn(ColumnAxis.NOW)


def _all_items(target: BoardTarget) -> list[dict[str, Any]]:
    reply = json.loads(run("project", "item-list", str(target.project.root), "--owner", target.owner.root, "--format", "json", "--limit", "500"))
    if reply.get("totalCount", 0) > len(reply["items"]):
        raise RuntimeError(f"board survey truncated — {len(reply['items'])} of {reply['totalCount']} cards fetched")
    return reply["items"]


def _board_columns(target: BoardTarget) -> dict[IssueNumber, BoardColumn]:
    """Every card's column as a typed map, from a single board fetch — so a caller checking several
    cards' columns pays one list, not one per card. The raw item dict is parsed to typed values here
    and never escapes; a card whose status is outside the known columns is simply absent from the map."""
    columns: dict[IssueNumber, BoardColumn] = {}
    for item in _all_items(target):
        raw_number = (item.get("content") or {}).get("number")
        axis = _COLUMN_BY_GH.get(item.get("status") or "")
        if raw_number is not None and axis is not None:
            columns[IssueNumber(raw_number)] = BoardColumn(axis)
    return columns


def _is_epic(record: IssueRecord) -> bool:
    return len(record.sub_issues) > 0


def _story_contract(record: IssueRecord) -> StoryBody | None:
    """The story contract a record's body carries, or None when it carries none — an epic, or a card
    predating the contract discipline. Absence is a real, not-exceptional case (the same stance
    `IssueRecord.label` takes); reads render what exists, and gates treat it as not provable."""
    if record.label is None:
        return None
    try:
        return StoryBody.from_markdown(record.label, record.body.root)
    except ValueError:
        return None


def _story_complete(record: IssueRecord) -> bool:
    """A story is complete when it is closed (Done) and every Task and Definition-of-Done box on its
    contract is checked — a body that carries no parseable contract proves nothing and is not
    complete. Takes an already-fetched record so a caller batching sub-issues does not re-fetch it."""
    if not isinstance(record.state, ClosedIssue):
        return False
    body = _story_contract(record)
    if body is None:
        return False
    tasks, dod = body.tasks.completion, body.definition_of_done.completion
    return tasks.checked == tasks.total and dod.checked == dod.total


def _story_start_tag(number: IssueNumber) -> str:
    """The one place the story-start anchor tag name is formed, so its creation and its read cannot
    drift apart."""
    return f"plan/story-start/{number.root}"


_EPIC_BRANCH_QUERY = (
    "query($owner:String!,$name:String!,$after:String){repository(owner:$owner,name:$name){"
    "issues(first:100,after:$after,states:OPEN){pageInfo{hasNextPage endCursor}nodes{"
    "subIssues{totalCount}linkedBranches(first:10){nodes{ref{name}}}}}}}"
)


def _epic_linked_branches(target: BoardTarget) -> set[BranchRef]:
    """Every branch the board links to an open epic (an issue that has sub-issues). This is what
    distinguishes a prior epic's branch from an unrelated branch (a dependabot or feature ref) that
    git alone cannot tell apart."""
    branches: set[BranchRef] = set()
    cursor: str | None = None
    while True:
        conn = graphql(_EPIC_BRANCH_QUERY, owner=target.owner.root, name=target.repo.root, after=cursor)["repository"]["issues"]
        for node in conn["nodes"]:
            if node["subIssues"]["totalCount"] > 0:
                branches.update(BranchRef(lb["ref"]["name"]) for lb in node["linkedBranches"]["nodes"] if lb.get("ref"))
        if not conn["pageInfo"]["hasNextPage"]:
            return branches
        cursor = conn["pageInfo"]["endCursor"]


@mcp.tool(
    name="start_epic",
    description="Gated epic entry: clean tree (never stash to pass), HEAD on main, main≈origin/main, "
    "branch unused, open epic with stories, no prior unmerged epic branch. On pass: create "
    "branch_name off main, link it, move epic to Now. Epics never enter In Progress.",
)
def start_epic(number: IssueNumber, branch_name: BranchRef, target: BoardTarget | None = None) -> str:
    target = _board(target)
    if not git.working_tree_clean():
        raise DirtyWorkingTree()
    on = git.current_branch()
    if on != git.MAIN:
        raise NotOnMain(on)
    git.fetch()
    behind = git.behind_upstream(git.MAIN)
    if behind.root > 0:
        raise MainBehindRemote(behind)
    if git.branch_exists_local(branch_name) or git.branch_exists_remote(branch_name):
        raise BranchAlreadyExists(branch_name)
    record = IssueRecord.fetch(number, target)
    if isinstance(record.state, ClosedIssue) or not _is_epic(record):
        raise NotAnEpicWithStories(number)
    if _linked_branches(number, target):
        raise EpicAlreadyStarted(number)
    unmerged = git.unmerged_branches(exclude={branch_name})
    if unmerged:
        prior = set(unmerged) & _epic_linked_branches(target)
        if prior:
            raise PriorEpicUnfinished(sorted(prior, key=lambda b: b.root)[0])
    run("issue", "develop", str(number.root), "--repo", f"{target.owner.root}/{target.repo.root}", "--name", branch_name.root, "--base", "main")
    try:
        _set_column(number, ToNow(), target)
    except Exception as move_error:
        try:
            git.delete_branch(branch_name)  # compensate: undo the branch a half-started epic left behind
        except Exception as cleanup_error:
            raise RuntimeError(
                f"start_epic: board move failed AND branch cleanup failed — remote branch "
                f"'{branch_name.root}' may still exist. move error: {move_error}; cleanup: {cleanup_error}"
            ) from move_error
        raise
    return f"start_epic: #{number.root} on {branch_name.root} — epic in Now, branch linked"


@mcp.tool(
    name="start_story",
    description="Gated next-story entry on the active epic branch: clean tree (never stash), "
    "epic in Now with linked branch, HEAD on that branch, no in-flight git op, no sibling In "
    "Progress, number is next unstarted sub-issue, preceding story Done with work on branch. On "
    "pass: In Progress + story-start tag. Then run-story: demolition → T# loop → Final QA.",
)
def start_story(number: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    record = IssueRecord.fetch(number, target)
    if not isinstance(record.parent, ParentDeclared):
        raise StoryHasNoActiveEpic(number)
    epic = record.parent.epic
    branches = _linked_branches(epic, target)
    columns = _board_columns(target)
    if not branches or columns.get(epic) != _NOW:
        raise StoryHasNoActiveEpic(number)
    epic_branch = branches[0]
    on = git.current_branch()
    if on != epic_branch:
        raise NotOnEpicBranch(on, epic_branch)
    if git.operation_in_progress():
        raise OperationInProgress()
    if not git.working_tree_clean():
        raise DirtyWorkingTree()
    git.fetch()
    if git.diverged_from_remote(epic_branch):
        raise EpicBranchDiverged(epic_branch)
    order = tuple(s.number for s in IssueRecord.fetch(epic, target).sub_issues)
    for sibling in order:
        if sibling.root != number.root and columns.get(sibling) == _IN_PROGRESS:
            raise SiblingStoryInProgress(sibling)
    records = {r.number.root: r for r in IssueRecord.fetch_many(order, target)}
    next_unstarted = next(
        (s for s in order if not isinstance(records[s.root].state, ClosedIssue)), None
    )
    if next_unstarted is None or next_unstarted.root != number.root:
        raise NotNextStory(number, next_unstarted)
    idx = [s.root for s in order].index(number.root)
    if idx > 0:
        preceding = order[idx - 1]
        if not _story_complete(records[preceding.root]):
            raise PrecedingStoryIncomplete(preceding)
        anchor = git.tag_ref(_story_start_tag(preceding))
        since = git.commits_between(anchor, epic_branch.root) if anchor else git.commits_ahead_of(git.MAIN, epic_branch)
        if since.root < 1:
            raise NoWorkOnEpicBranch(epic_branch)
    _set_column(number, ToInProgress(branch=epic_branch), target)
    git.tag_head(_story_start_tag(number))  # anchor: the epic-branch HEAD at this story's start
    return f"start_story: #{number.root} In Progress on {epic_branch.root}"


@mcp.tool(
    name="finish_epic",
    description="Finish the active epic — the gated exit matching start_epic's gated entry — after "
    "deterministic safety checks: number is an open epic, in Now with a linked branch; every "
    "story is Done with all Task and Definition-of-Done boxes checked; local main is level with "
    "origin/main; the epic branch carries no commit missing from main. On pass: move the epic to "
    "Done, drop focus, and close the epic issue — Done and closed are one fact, owned by this "
    "flow. Merging the branch is git work this tool verifies but never performs.",
)
def finish_epic(number: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    record = IssueRecord.fetch(number, target)
    if isinstance(record.state, ClosedIssue) or not _is_epic(record):
        raise NotAnEpicWithStories(number)
    if _board_columns(target).get(number) != _NOW:
        raise EpicNotActive(number)
    branches = _linked_branches(number, target)
    if not branches:
        raise EpicBranchMissing(number)
    stories = IssueRecord.fetch_many(tuple(s.number for s in record.sub_issues), target)
    for story in stories:
        if not _story_complete(story):
            raise StoryNotComplete(story.number)
    git.fetch()
    behind = git.behind_upstream(git.MAIN)
    if behind.root > 0:
        raise MainBehindRemote(behind)
    # The branch may live only on origin (never checked out here) — count against whichever ref
    # exists; a branch already deleted after merge counts 0 from both and passes.
    ahead = git.commits_between(git.MAIN.root, branches[0].root)
    if ahead.root == 0:
        ahead = git.commits_between(git.MAIN.root, f"origin/{branches[0].root}")
    if ahead.root > 0:
        raise EpicBranchUnmerged(branches[0], ahead)
    _set_column(number, ToDone(), target)
    _close_issue(number, target)  # the gate proved it open; Done and closed are one fact
    return f"finish_epic: #{number.root} Done and closed — {len(stories)} stories complete, {branches[0].root} merged"


@mcp.tool(
    name="move_to_blocked",
    description="Move any card to Blocked, posting the named technical blocker as a comment in the "
    "same motion — a card cannot enter Blocked with nothing blocking it. Removes the focus label "
    "if present.",
)
def move_to_blocked(number: IssueNumber, blocker: CommentText, target: BoardTarget | None = None) -> str:
    target = _board(target)
    _set_column(number, ToBlocked(blocker=blocker), target)
    return f"move_to_blocked: #{number.root}"


@mcp.tool(
    name="move_to_done",
    description="Move card to Done + close issue. Story contracts refuse while any Tasks or "
    "Definition of Done box is unchecked — Tasks via judge/check_story_task, DoD via parent "
    "check_final_qa after Final QA. Active epic: prefer finish_epic.",
)
def move_to_done(number: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    record = IssueRecord.fetch(number, target)
    story = _story_contract(record)  # epics and pre-discipline cards carry no contract to hold them to
    if story is not None:
        tasks, dod = story.tasks.completion, story.definition_of_done.completion
        if tasks.checked != tasks.total or dod.checked != dod.total:
            raise ValueError(
                f"#{number.root} is not complete — tasks {tasks.rendered}, "
                f"definition_of_done {dod.rendered}; Done requires every box checked"
            )
    _set_column(number, ToDone(), target)
    if isinstance(record.state, OpenIssue):
        _close_issue(number, target)
    return f"move_to_done: #{number.root} Done and closed"


_POSITION_MUTATION = (
    "mutation($p: ID!, $i: ID!, $a: ID) { updateProjectV2ItemPosition("
    "input: {projectId: $p, itemId: $i, afterId: $a}) { clientMutationId } }"
)


@mcp.tool(
    name="reorder_card",
    description="Move a card within the board's item order: to the top, or directly after another "
    "card. Position is the board's one priority axis — a column view shows its slice of the single "
    "project order, so top of the order is top of the card's column. Use to put an epic at the top "
    "of Now, or to sequence cards sharing a column.",
)
def reorder_card(number: IssueNumber, anchor: CardAnchor, target: BoardTarget | None = None) -> str:
    target = _board(target)
    item_id = _card_id(number, target)
    if item_id is None:
        raise RuntimeError(f"#{number.root} has no card on the board — surface the drift, don't repair it")
    project_id, _, _ = _status_field(target)
    args = ["api", "graphql", "-F", f"p={project_id}", "-F", f"i={item_id}", "-f", f"query={_POSITION_MUTATION}"]
    if isinstance(anchor, AfterCard):
        after_id = _card_id(anchor.card, target)
        if after_id is None:
            raise RuntimeError(f"anchor #{anchor.card.root} has no card on the board")
        args += ["-F", f"a={after_id}"]
        run(*args)
        return f"reorder_card: #{number.root} after #{anchor.card.root}"
    run(*args)
    return f"reorder_card: #{number.root} to top"


_REPRIORITIZE_AFTER = (
    "mutation($p: ID!, $c: ID!, $a: ID!) { reprioritizeSubIssue("
    "input: {issueId: $p, subIssueId: $c, afterId: $a}) { issue { number } } }"
)
_REPRIORITIZE_BEFORE = (
    "mutation($p: ID!, $c: ID!, $b: ID!) { reprioritizeSubIssue("
    "input: {issueId: $p, subIssueId: $c, beforeId: $b}) { issue { number } } }"
)


@mcp.tool(
    name="reorder_story_in_epic",
    description="Move a story within its epic's execution order — the sub-issue list start_story "
    "walks: to first, or directly after a named sibling. Use to re-sequence an epic's stories; "
    "for a card's position within a board column use reorder_card.",
)
def reorder_story_in_epic(
    epic: IssueNumber, story: IssueNumber, anchor: SiblingAnchor, target: BoardTarget | None = None,
) -> str:
    target = _board(target)
    siblings = [s.number.root for s in IssueRecord.fetch(epic, target).sub_issues]
    if story.root not in siblings:
        raise ValueError(f"#{story.root} is not a sub-issue of #{epic.root}")
    parent_id = IssueRecord.node_id(epic, target)
    child_id = IssueRecord.node_id(story, target)
    if isinstance(anchor, ToFirst):
        if siblings[0] == story.root:
            return f"reorder_story_in_epic: #{story.root} already first in #{epic.root}"
        before_id = IssueRecord.node_id(IssueNumber(siblings[0]), target)
        run("api", "graphql", "-F", f"p={parent_id}", "-F", f"c={child_id}", "-F", f"b={before_id}",
            "-f", f"query={_REPRIORITIZE_BEFORE}")
        return f"reorder_story_in_epic: #{story.root} first in #{epic.root}"
    if anchor.sibling.root == story.root:
        raise ValueError(f"#{story.root} cannot anchor after itself")
    if anchor.sibling.root not in siblings:
        raise ValueError(f"anchor #{anchor.sibling.root} is not a sub-issue of #{epic.root}")
    after_id = IssueRecord.node_id(anchor.sibling, target)
    run("api", "graphql", "-F", f"p={parent_id}", "-F", f"c={child_id}", "-F", f"a={after_id}",
        "-f", f"query={_REPRIORITIZE_AFTER}")
    return f"reorder_story_in_epic: #{story.root} after #{anchor.sibling.root} in #{epic.root}"


@mcp.tool(
    name="read_issues",
    description="The fast typed reader: one compact rendering per issue — title, state, label, "
    "parent, sub-issues, body, comments — any count of numbers in one crossing. Use this instead "
    "of raw gh issue view. When you don't know the numbers yet, read_board_status or read_column "
    "finds them; for an epic with all its stories, read_epic.",
)
def read_issues(numbers: tuple[IssueNumber, ...], target: BoardTarget | None = None) -> str:
    target = _board(target)
    divider = "\n\n" + "=" * 40 + "\n\n"
    return divider.join(r.rendered for r in IssueRecord.fetch_many(numbers, target))


@mcp.tool(
    name="delete_issues",
    description="Permanently delete issues. Each deletion names the number AND the exact title the "
    "caller believes it carries; any mismatch refuses the whole batch before anything is destroyed "
    "— deleting the wrong number is unrepresentable, not just regrettable. GitHub's delete "
    "cascades: the card leaves the board and sub-issue relations die with the issue. Irreversible "
    "— operator-ordered deletions only.",
)
def delete_issues(deletions: tuple[Deletion, ...], target: BoardTarget | None = None) -> str:
    target = _board(target)
    records = IssueRecord.fetch_many(tuple(d.number for d in deletions), target)
    mismatches = [
        f"#{d.number.root} is '{r.title.root}', not '{d.title.root}'"
        for d, r in zip(deletions, records)
        if r.title.root != d.title.root
    ]
    if mismatches:
        raise ValueError("refusing every deletion — " + "; ".join(mismatches))
    for d in deletions:
        _delete_issue(d.number, target)
    return "delete_issues: " + " ".join(f"#{d.number.root}" for d in deletions)


@mcp.tool(
    name="rename_story",
    description="Rename a story's title. Does not touch its body or label.",
)
def rename_story(number: IssueNumber, name: StoryName, target: BoardTarget | None = None) -> str:
    target = _board(target)
    _rename_issue(number, name, target)
    return f"rename_story: #{number.root}"


@mcp.tool(
    name="read_column",
    description="Survey one board column: every card currently in Backlog, Later, Next, Now, In "
    "Progress, Blocked, or Done, optionally filtered to one classification label or to "
    "focus-labeled cards only. Answers 'what's queued in X' when you don't know issue numbers. "
    "Pure read. For the whole working picture — In Progress, Blocked, and Now together with "
    "progress counts — use read_board_status.",
)
def read_column(
    column: BoardColumn, label: IssueLabel | None = None, focus_only: bool = False,
    target: BoardTarget | None = None,
) -> str:
    target = _board(target)
    survey = BoardSurvey.fetch(column, label, focus_only, target)
    if not survey.root:
        return f"read_column: {column.root.value} — no cards"
    return "\n".join(e.rendered for e in survey.root)


@mcp.tool(
    name="read_epic",
    description="Read an epic together with every one of its sub-issue stories, full bodies "
    "included, rendered as one report. Use instead of read_issues plus a manual second call per "
    "sub-issue when you need the whole body of work an epic groups. For just the completion "
    "rollup — columns and counts, no bodies — read_epic_progress is the cheap sibling.",
)
def read_epic(number: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    epic = IssueRecord.fetch(number, target)
    divider = "\n\n" + "=" * 40 + "\n\n"
    stories = IssueRecord.fetch_many(tuple(s.number for s in epic.sub_issues), target) if epic.sub_issues else ()
    return divider.join([epic.rendered, *(s.rendered for s in stories)])


@mcp.tool(
    name="read_story_progress",
    description="Report a story's Tasks and Definition of Done completion as checked/total counts, "
    "derived from its current body. Use to decide whether a story is actually ready to move to Done "
    "without re-reading and hand-counting the checklist yourself. Pure read; for the lists "
    "themselves, T#s and all, use read_story_tasks.",
)
def read_story_progress(number: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    story = _current_story(number, target)
    return (
        f"read_story_progress: #{number.root} "
        f"tasks={story.tasks.completion.rendered} "
        f"definition_of_done={story.definition_of_done.completion.rendered}"
    )


@mcp.tool(
    name="read_story_tasks",
    description="A story's Tasks and Definition of Done lists verbatim — T# identifiers, checked "
    "state, and text — without the rest of the contract. The slice between read_story_progress "
    "(counts only) and read_issues (the whole issue); use it to pick the next task or confirm a "
    "check-off landed.",
)
def read_story_tasks(number: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    story = _current_story(number, target)
    return "\n".join([
        f"read_story_tasks: #{number.root} tasks {story.tasks.completion.rendered}, "
        f"definition_of_done {story.definition_of_done.completion.rendered}",
        "",
        "Tasks:",
        *[t.markdown for t in story.tasks.root],
        "",
        "Definition of Done:",
        *[t.markdown for t in story.definition_of_done.root],
    ])


@mcp.tool(
    name="read_epic_progress",
    description="An epic's rollup, one line per story in execution order: board column, open/closed "
    "state, and tasks/DoD counts, with no body text. The cheap sibling of read_epic — use it to see "
    "how far an epic is; use read_epic when you need the stories' full contracts.",
)
def read_epic_progress(number: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    epic = IssueRecord.fetch(number, target)
    if not _is_epic(epic):
        raise ValueError(f"#{number.root} has no sub-issues — not an epic this report covers")
    stories = IssueRecord.fetch_many(tuple(s.number for s in epic.sub_issues), target)
    columns = _board_columns(target)
    complete = sum(1 for s in stories if _story_complete(s))
    lines = [f"read_epic_progress: #{number.root} {epic.title.root} — {complete}/{len(stories)} stories complete"]
    for story in stories:
        column = columns.get(story.number)
        where = GH_COLUMN[column.root] if column is not None else "no card"
        contract = _story_contract(story)
        counts = (
            f"tasks {contract.tasks.completion.rendered}, dod {contract.definition_of_done.completion.rendered}"
            if contract is not None
            else "no contract"
        )
        lines.append(f"#{story.number.root} [{where}] {story.state.state.value} — {counts} — {story.title.root}")
    return "\n".join(lines)


@mcp.tool(
    name="read_next_story",
    description="A dry run of start_story's board-side gate for an epic: whether the epic is In "
    "Progress with a linked branch, which story is next in execution order, and whether the "
    "preceding story is provably complete — the facts that decide a start, with no mutation. The "
    "git-side checks (clean tree, HEAD on the epic branch, divergence) remain start_story's own, "
    "verified at the moment of the start.",
)
def read_next_story(epic: IssueNumber, target: BoardTarget | None = None) -> str:
    target = _board(target)
    record = IssueRecord.fetch(epic, target)
    if not _is_epic(record):
        raise ValueError(f"#{epic.root} has no sub-issues — not an epic")
    branches = _linked_branches(epic, target)
    active = _board_columns(target).get(epic) == _NOW and bool(branches)
    order = tuple(s.number for s in record.sub_issues)
    records = {r.number.root: r for r in IssueRecord.fetch_many(order, target)}
    lines = [
        f"read_next_story: epic #{epic.root} "
        + (
            f"active on {branches[0].root}"
            if active
            else "not startable — needs the epic in Now with a linked branch (start_epic)"
        )
    ]
    next_unstarted = next((s for s in order if not isinstance(records[s.root].state, ClosedIssue)), None)
    if next_unstarted is None:
        lines.append("next: none — every story is closed; the epic is ready to finish (finish_epic)")
        return "\n".join(lines)
    lines.append(f"next: #{next_unstarted.root} {records[next_unstarted.root].title.root}")
    idx = [s.root for s in order].index(next_unstarted.root)
    if idx > 0:
        preceding = order[idx - 1]
        verdict = "complete" if _story_complete(records[preceding.root]) else "NOT complete — start_story will refuse"
        lines.append(f"preceding #{preceding.root}: {verdict}")
    return "\n".join(lines)


@mcp.tool(
    name="read_board_status",
    description="The zero-argument orientation read: every In Progress and Blocked card with its "
    "story task/DoD counts, parent epic, epic branch, and blocker, plus the Now column — one call "
    "answering 'where is the work right now'. Pure read. For one column use read_column; for one "
    "epic's rollup use read_epic_progress.",
    meta={"anthropic/alwaysLoad": True},
)
def read_board_status(target: BoardTarget | None = None) -> str:
    target = _board(target)
    entries: dict[ColumnAxis, list[BoardEntry]] = {}
    for item in _all_items(target):
        content = item.get("content") or {}
        axis = _COLUMN_BY_GH.get(item.get("status") or "")
        if content.get("number") is None or axis is None:
            continue
        item_labels = item.get("labels", [])
        member = next(
            (m for n in item_labels if (m := LabelName.observed(str(n))) is not None),
            None,
        )
        entries.setdefault(axis, []).append(BoardEntry(
            number=IssueNumber(content["number"]),
            title=IssueTitle(content["title"]),
            label=IssueLabel(member) if member is not None else None,
            focus=any(str(n).casefold() == "focus" for n in item_labels),
        ))
    active = [e.number for axis in (ColumnAxis.IN_PROGRESS, ColumnAxis.BLOCKED) for e in entries.get(axis, [])]
    records = {r.number.root: r for r in IssueRecord.fetch_many(tuple(active), target)} if active else {}
    related = {
        n.root
        for r in records.values()
        for n in (
            tuple(s.number for s in r.sub_issues)
            if _is_epic(r)
            else (r.parent.epic,) if isinstance(r.parent, ParentDeclared) else ()
        )
    } - set(records)
    if related:
        fetched = IssueRecord.fetch_many(tuple(IssueNumber(n) for n in sorted(related)), target)
        records |= {r.number.root: r for r in fetched}

    def detail(entry: BoardEntry, blocked: bool = False) -> str:
        record = records[entry.number.root]
        parts = [entry.rendered]
        if _is_epic(record):
            subs = [records[s.number.root] for s in record.sub_issues if s.number.root in records]
            parts.append(f"stories {sum(1 for s in subs if _story_complete(s))}/{len(subs)} complete")
            if record.linked_branches:
                parts.append(f"branch {record.linked_branches[0].root}")
        else:
            contract = _story_contract(record)
            if contract is not None:
                parts.append(
                    f"tasks {contract.tasks.completion.rendered}, "
                    f"dod {contract.definition_of_done.completion.rendered}"
                )
            if isinstance(record.parent, ParentDeclared):
                parent = records.get(record.parent.epic.root)
                branch = f" on {parent.linked_branches[0].root}" if parent is not None and parent.linked_branches else ""
                parts.append(f"epic #{record.parent.epic.root}{branch}")
        if blocked:
            # The blocker rides the most recent "Blocked:" comment move_to_blocked posted.
            blockers = [c.text.root for c in record.comments if c.text.root.startswith("Blocked:")]
            if blockers:
                parts.append(blockers[-1])
        return " — ".join(parts)

    def section(title: str, axis: ColumnAxis, render: Callable[[BoardEntry], str]) -> list[str]:
        rows = entries.get(axis, [])
        return [f"{title}:", *([render(e) for e in rows] if rows else ["(none)"]), ""]

    return "\n".join([
        "read_board_status:",
        "",
        *section("In Progress", ColumnAxis.IN_PROGRESS, detail),
        *section("Blocked", ColumnAxis.BLOCKED, lambda e: detail(e, blocked=True)),
        *section("Now", ColumnAxis.NOW, lambda e: e.rendered),
    ]).rstrip()
