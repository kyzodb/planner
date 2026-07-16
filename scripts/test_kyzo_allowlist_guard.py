#!/usr/bin/env python3
"""Unit tests for kyzo_allowlist_guard — run: python3 mcp/scripts/test_kyzo_allowlist_guard.py"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

GUARD = Path(__file__).resolve().parent / "kyzo_allowlist_guard.py"
PYTHON = "/usr/bin/python3"


def _run(
    payload: dict,
    *,
    allowlist: list[str] | None,
    session: bool,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    with tempfile.TemporaryDirectory() as tmp:
        session_path = Path(tmp) / "task-session.json"
        if session:
            session_path.write_text(
                json.dumps({"allowlist": allowlist or ["crates/foo/**"], "offenses": 0}) + "\n"
            )
            env["KYZO_TASK_SESSION"] = str(session_path)
        else:
            env.pop("KYZO_TASK_SESSION", None)
        return subprocess.run(
            [PYTHON, str(GUARD)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )


def _bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _edit(path: str) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": path}}


def test_no_session_allows_git() -> None:
    r = _run(_bash("git status"), allowlist=None, session=False)
    assert r.returncode == 0, r.stderr


def test_armed_denies_git_status() -> None:
    r = _run(_bash("git status"), allowlist=["crates/foo/**"], session=True)
    assert r.returncode == 2, r.stderr
    assert "git is denied" in r.stderr


def test_armed_denies_git_diff() -> None:
    r = _run(
        _bash("git diff --name-only HEAD"),
        allowlist=["crates/foo/**"],
        session=True,
    )
    assert r.returncode == 2, r.stderr


def test_armed_denies_git_in_pipeline() -> None:
    r = _run(
        _bash("cd crates/foo && git stash"),
        allowlist=["crates/foo/**"],
        session=True,
    )
    assert r.returncode == 2, r.stderr


def test_armed_allows_check_command() -> None:
    r = _run(
        _bash("cargo check --workspace --all-targets"),
        allowlist=["crates/foo/**"],
        session=True,
    )
    assert r.returncode == 0, r.stderr


def test_armed_denies_offlist_edit() -> None:
    r = _run(
        _edit("crates/other/src/lib.rs"),
        allowlist=["crates/foo/**"],
        session=True,
    )
    assert r.returncode == 2, r.stderr


def test_armed_allows_onlist_edit() -> None:
    r = _run(
        _edit("crates/foo/src/lib.rs"),
        allowlist=["crates/foo/**"],
        session=True,
    )
    assert r.returncode == 0, r.stderr


def main() -> None:
    tests = [
        test_no_session_allows_git,
        test_armed_denies_git_status,
        test_armed_denies_git_diff,
        test_armed_denies_git_in_pipeline,
        test_armed_allows_check_command,
        test_armed_denies_offlist_edit,
        test_armed_allows_onlist_edit,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"ok  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}", file=sys.stderr)
    if failed:
        raise SystemExit(1)
    print(f"{len(tests)} passed")


if __name__ == "__main__":
    main()
