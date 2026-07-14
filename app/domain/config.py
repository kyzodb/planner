"""The program's one environment read (prefix `PLANNER_`), proven once at mount into typed
values, plus the board-identity vocabulary those values are made of. Resolution of the *default*
board — deriving whatever the environment leaves unset from the checkout itself — is
`app.domain.target`'s job; this file only proves what was actually given. Identity is `gh`'s
problem, not ours: whatever repo/project a caller names, `gh` acts as the authenticated account."""

import os

from pydantic import BaseModel, ConfigDict, Field, RootModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class RepoOwner(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class RepoName(RootModel[str], frozen=True):
    root: str = Field(min_length=1)


class ProjectNumber(RootModel[int], frozen=True):
    root: int = Field(gt=0)


class RepoRoot(RootModel[str], frozen=True):
    """Path of the git repository whose branches the lifecycle gates read and write."""

    root: str = Field(min_length=1)


class RepoIdentity(BaseModel):
    """A repository named whole — owner and name together, the unit a checkout's `origin` yields."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    owner: RepoOwner
    name: RepoName


class BoardTarget(BaseModel):
    """The owner, repo, and project number a board tool acts against — always given as one unit,
    since a repo without its owner or project number doesn't identify a board."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    owner: RepoOwner
    repo: RepoName
    project: ProjectNumber


class PlannerSettings(BaseSettings):
    """The one structure that reads the environment. Every board field is an override: `None`
    means "derive from the checkout" and is resolved by `app.domain.target` at mount. An empty
    env value counts as unset — a plugin host substituting an unfilled option passes empty, and
    empty is not a name."""

    model_config = SettingsConfigDict(
        frozen=True, extra="forbid", env_prefix="PLANNER_", env_ignore_empty=True
    )
    board_owner: RepoOwner | None = None
    board_repo: RepoName | None = None
    board_project: ProjectNumber | None = None
    repo: RepoRoot = Field(default_factory=lambda: RepoRoot(os.getcwd()))


SETTINGS = PlannerSettings()  # pyright: ignore[reportCallIssue]  — fields fill from the environment
