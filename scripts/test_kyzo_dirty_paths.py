#!/usr/bin/env python3
"""Unit tests for git.paths_from_porcelain — run: python3 mcp/scripts/test_kyzo_dirty_paths.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.domain.git import paths_from_porcelain  # noqa: E402


def test_empty() -> None:
    assert paths_from_porcelain("") == ()


def test_modified_and_untracked() -> None:
    out = " M crates/foo/a.rs\n?? crates/foo/b.rs\n"
    assert paths_from_porcelain(out) == ("crates/foo/a.rs", "crates/foo/b.rs")


def test_rename_uses_target() -> None:
    out = "R  old.rs -> new.rs\n"
    assert paths_from_porcelain(out) == ("new.rs",)


def test_staged() -> None:
    out = "M  staged.rs\n"
    assert paths_from_porcelain(out) == ("staged.rs",)


def main() -> None:
    tests = [test_empty, test_modified_and_untracked, test_rename_uses_target, test_staged]
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
