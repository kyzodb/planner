"""The one place `git` the subprocess is spawned, against the repo the board's branches live in
(`SETTINGS.repo`, the configured `PLAN_REPO`). Branch identities cross this boundary as
`BranchRef`; only the private `_git` layer and the rev-level helpers (tags, commit ranges) speak raw
strings, because a tag or a commit-range endpoint is an arbitrary git rev, not a branch. The readers
never mutate the tree; the two writers — the story-start anchor tag and the compensation branch
delete — are named as such at their call sites."""

import os
import re
import subprocess

from app.domain.config import SETTINGS, RepoIdentity, RepoName, RepoOwner
from app.domain.type import BranchRef, CommitCount

REPO = os.path.abspath(SETTINGS.repo.root)
MAIN = BranchRef("main")


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)


def _ok(*args: str) -> bool:
    return _git(*args).returncode == 0


def _count(rev_range: str) -> int:
    out = _git("rev-list", "--count", rev_range).stdout.strip()
    return int(out) if out.isdigit() else 0


def _resolves(rev: str) -> bool:
    return _ok("rev-parse", "--verify", "--quiet", rev)


def fetch() -> None:
    """Refresh remote-tracking refs so behind/diverged reads are against current truth."""
    _git("fetch", "origin", "--quiet")


def working_tree_clean() -> bool:
    """No unstaged, staged, or untracked change — `git status --porcelain` is empty."""
    return _git("status", "--porcelain").stdout.strip() == ""


def current_branch() -> BranchRef | None:
    """The checked-out branch, or None when HEAD is detached (no branch identity to name)."""
    name = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    return BranchRef(name) if name and name != "HEAD" else None


def operation_in_progress() -> bool:
    """A merge, rebase, cherry-pick, revert, or bisect is mid-flight — HEAD is not at rest."""
    git_dir = _git("rev-parse", "--git-dir").stdout.strip()
    base = git_dir if os.path.isabs(git_dir) else os.path.join(REPO, git_dir)
    return any(
        os.path.exists(os.path.join(base, marker))
        for marker in ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG")
    )


def branch_exists_local(name: BranchRef) -> bool:
    return _resolves(f"refs/heads/{name.root}")


def branch_exists_remote(name: BranchRef) -> bool:
    return _git("ls-remote", "--heads", "origin", name.root).stdout.strip() != ""


def behind_upstream(branch: BranchRef) -> CommitCount:
    """Commits on `origin/<branch>` not yet in local `<branch>` (0 if no such remote branch)."""
    upstream = f"origin/{branch.root}"
    return CommitCount(_count(f"{branch.root}..{upstream}") if _resolves(upstream) else 0)


def diverged_from_remote(branch: BranchRef) -> bool:
    """Local and remote have each advanced independently — a non-fast-forwardable split. False when
    there is no remote branch yet (nothing to diverge from)."""
    upstream = f"origin/{branch.root}"
    if not _resolves(upstream):
        return False
    return _count(f"{upstream}..{branch.root}") > 0 and _count(f"{branch.root}..{upstream}") > 0


def commits_ahead_of(base: BranchRef, branch: BranchRef) -> CommitCount:
    """Commits on `branch` not on `base` — the work landed on the branch past its start point."""
    if not (_resolves(base.root) and _resolves(branch.root)):
        return CommitCount(0)
    return CommitCount(_count(f"{base.root}..{branch.root}"))


def is_merged_into(branch: BranchRef, into: BranchRef) -> bool:
    """`branch`'s tip is an ancestor of `into` — every commit on it is already in `into`."""
    if not _git("rev-parse", "--verify", "--quiet", branch.root).stdout.strip():
        return True  # a branch that does not exist locally is, for the prior-epic check, "gone"
    return _ok("merge-base", "--is-ancestor", branch.root, into.root)


def unmerged_branches(exclude: set[BranchRef]) -> list[BranchRef]:
    """Every branch — local or on origin — carrying commits not yet merged into main, deduplicated
    by short name. `main`, `HEAD`, and names in `exclude` are omitted."""
    out = _git("branch", "-a", "--no-merged", MAIN.root, "--format", "%(refname:short)").stdout
    excluded = {b.root for b in exclude} | {MAIN.root, "HEAD"}
    seen: set[str] = set()
    result: list[BranchRef] = []
    for line in out.splitlines():
        name = line.strip()
        short = name[len("origin/") :] if name.startswith("origin/") else name
        if not short or short in excluded or short in seen:
            continue
        seen.add(short)
        result.append(BranchRef(short))
    return result


def delete_branch(name: BranchRef) -> None:
    """Remove a branch locally and on origin — the compensation for a half-started epic whose board
    move failed after the branch was created. Raises if the remote delete fails, so a failed
    rollback is surfaced rather than silently leaving the branch behind."""
    _git("branch", "-D", name.root)  # local ref may not exist (branch was created remotely); ignore
    result = _git("push", "origin", "--delete", name.root)
    if result.returncode != 0:
        raise RuntimeError(f"could not delete remote branch '{name.root}': {result.stderr.strip()}")


# --- Rev-level helpers: a tag name and a commit-range endpoint are arbitrary git revs, not branch
#     identities, so they stay strings. ---


def commits_between(start_rev: str, end_rev: str) -> CommitCount:
    """Commits reachable from `end_rev` but not `start_rev` — the work landed since `start_rev`.
    0 when `start_rev` does not resolve (an anchor that was never recorded)."""
    return CommitCount(_count(f"{start_rev}..{end_rev}") if _resolves(start_rev) else 0)


def changed_paths(base_rev: str, end_rev: str = "HEAD") -> tuple[str, ...]:
    """Paths changed between two revs (`git diff --name-only`). Empty when `base_rev` does not resolve."""
    if not _resolves(base_rev):
        return ()
    out = _git("diff", "--name-only", f"{base_rev}...{end_rev}").stdout
    return tuple(line.strip() for line in out.splitlines() if line.strip())


def paths_from_porcelain(out: str) -> tuple[str, ...]:
    """Parse `git status --porcelain` into unique paths (rename targets win). Pure — no subprocess."""
    paths: list[str] = []
    seen: set[str] = set()
    for line in out.splitlines():
        if len(line) < 4:
            continue
        rest = line[3:]
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1]
        path = rest.strip().strip('"')
        if path and path not in seen:
            seen.add(path)
            paths.append(path)
    return tuple(paths)


def dirty_paths() -> tuple[str, ...]:
    """Staged, unstaged, and untracked paths vs HEAD — the task WIP meter after parent commits."""
    return paths_from_porcelain(_git("status", "--porcelain", "-uall").stdout)


def tag_head(name: str) -> None:
    """Record the current HEAD under a lightweight tag, overwriting any prior tag of that name —
    the durable anchor for 'work since this story started'."""
    _git("tag", "-f", name)


def tag_ref(name: str) -> str | None:
    """The tag's ref for use as a rev, or None if the tag does not exist."""
    return f"refs/tags/{name}" if _resolves(f"refs/tags/{name}") else None


_ORIGIN_URL = re.compile(r"github\.com[:/](?P<owner>[^/]+)/(?P<name>[^/]+?)(?:\.git)?/?$")


def origin_identity() -> RepoIdentity:
    """The checkout's own GitHub identity, read off `origin` — the context read that lets an
    unconfigured board default to the repository it is standing in. No origin, or an origin this
    program cannot read an owner/name from, refuses by name instead of guessing."""
    result = _git("remote", "get-url", "origin")
    if result.returncode != 0:
        raise RuntimeError(
            f"plan: no board configured and no `origin` remote in {REPO} to derive one from — "
            "set PLAN_BOARD_OWNER/PLAN_BOARD_REPO or add the remote"
        )
    url = result.stdout.strip()
    match = _ORIGIN_URL.search(url)
    if match is None:
        raise RuntimeError(
            f"plan: `origin` ({url}) is not a GitHub remote this program can read an "
            "owner/repo from — set PLAN_BOARD_OWNER/PLAN_BOARD_REPO"
        )
    return RepoIdentity(owner=RepoOwner(match["owner"]), name=RepoName(match["name"]))
