#!/usr/bin/env python3
"""DoD = one Final QA — run: cd mcp && uv run python scripts/test_kyzo_dod_schema.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.domain.story import DefinitionOfDoneList, Task, _FINAL_QA_TEXT  # noqa: E402
from app.domain.type import CheckCommand, TaskText  # noqa: E402


def _item(text: str, *, checked: bool = False, check: str | None = None) -> Task:
    return Task(
        checked=checked,
        text=TaskText(text),
        check=CheckCommand(check) if check else None,
    )


def test_final_qa_ok() -> None:
    dod = DefinitionOfDoneList((_item("Final QA — parent confirms closure"),))
    assert dod.completion.total == 1
    assert dod.root[0].text.root.startswith("Final QA")


def test_multi_item_normalizes() -> None:
    dod = DefinitionOfDoneList(
        (
            _item("value change", checked=True),
            _item("condemned gone", checked=True),
            _item("`cargo test`", checked=True),
        )
    )
    assert dod.completion.total == 1
    assert dod.root[0].checked is True
    assert dod.root[0].text.root == _FINAL_QA_TEXT


def test_partial_stays_unchecked() -> None:
    dod = DefinitionOfDoneList(
        (
            _item("a", checked=True),
            _item("b", checked=False),
        )
    )
    assert dod.root[0].checked is False


def test_check_on_dod_strips() -> None:
    dod = DefinitionOfDoneList((_item("Final QA — x", check="cargo test"),))
    assert dod.root[0].check is None
    assert dod.root[0].text.root == _FINAL_QA_TEXT


def main() -> None:
    tests = [
        test_final_qa_ok,
        test_multi_item_normalizes,
        test_partial_stays_unchecked,
        test_check_on_dod_strips,
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
