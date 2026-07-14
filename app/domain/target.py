"""Resolution of the default board, on first need — never at import, so the server always
boots and `create_board` stays reachable on a repo that has no board yet: whatever `PLANNER_BOARD_*` left unset derives from the
checkout itself — owner and repo off `origin`, the project number off the repo's sole open linked
project. Selection only, never mutation: this file reads git and GitHub to *name* a target; every
write against that target is still schema-gated by the board recognizers, so a derived default
that points at a foreign board refuses on first touch instead of altering it."""

from typing import Self

from pydantic import BaseModel, ConfigDict

from app.domain import git
from app.domain.config import BoardTarget, PlannerSettings, ProjectNumber, RepoName, RepoOwner
from app.domain.gh import graphql
from app.domain.type import ProjectTitle


class LinkedProject(BaseModel):
    """One project linked to the repo, as GitHub reports it — the candidate pool the default
    board is chosen from."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    number: ProjectNumber
    title: ProjectTitle
    closed: bool

    @classmethod
    def from_graphql(cls, node: dict[str, object]) -> Self:
        return cls.model_validate(node)


_LINKED_PROJECTS_QUERY = (
    "query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) "
    "{ projectsV2(first: 20) { totalCount nodes { number title closed } } } }"
)


def _sole_open_project(owner: RepoOwner, repo: RepoName) -> ProjectNumber:
    """The repo's one open linked project — the default board. Zero or several open candidates is
    a refusal naming them, never a guess."""
    connection = graphql(_LINKED_PROJECTS_QUERY, owner=owner.root, name=repo.root)["repository"]["projectsV2"]
    projects = tuple(LinkedProject.from_graphql(node) for node in connection["nodes"])
    open_projects = tuple(p for p in projects if not p.closed)
    if len(open_projects) != 1:
        listed = ", ".join(f"#{p.number.root} {p.title.root}" for p in open_projects) or "none"
        raise RuntimeError(
            f"planner: {owner.root}/{repo.root} has {len(open_projects)} open linked projects "
            f"({listed}) — set PLANNER_BOARD_PROJECT to choose the board"
        )
    return open_projects[0].number


def configured_target(settings: PlannerSettings) -> BoardTarget:
    """The board the server acts on by default: each configured value taken as given, each unset
    one derived from the checkout. Fully-configured settings resolve with no git or network read."""
    owner, repo = settings.board_owner, settings.board_repo
    if owner is None or repo is None:
        identity = git.origin_identity()
        owner = owner if owner is not None else identity.owner
        repo = repo if repo is not None else identity.name
    project = settings.board_project if settings.board_project is not None else _sole_open_project(owner, repo)
    return BoardTarget(owner=owner, repo=repo, project=project)

