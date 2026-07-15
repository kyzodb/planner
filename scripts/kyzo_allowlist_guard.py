#!/usr/bin/env python3
"""PreToolUse: deny Read/Edit/Write (and path-bearing Bash) outside KYZO allowlist.

Expects env KYZO_TASK_SESSION pointing at a JSON file:
  {"allowlist": ["path/or/glob", ...], "offenses": 0}

Reads Claude Code hook JSON from stdin. Denies with exit 2 when path is off-list.
No session file → allow (orchestrator has not armed a task).
"""

from __future__ import annotations

import json
import os
import re
import sys
from fnmatch import fnmatch
from pathlib import Path


def _covers(path: str, allowlist: list[str]) -> bool:
    path = path.lstrip("./")
    for pat in allowlist:
        pat = pat.strip().strip("`")
        if any(ch in pat for ch in "*?["):
            if fnmatch(path, pat):
                return True
            continue
        if path == pat or path.startswith(pat.rstrip("/") + "/"):
            return True
    return False


def _paths_from_input(tool: str, tool_input: dict) -> list[str]:
    if tool in ("Read", "Edit", "Write"):
        p = tool_input.get("file_path") or tool_input.get("path")
        return [p] if isinstance(p, str) and p else []
    if tool == "Bash":
        cmd = tool_input.get("command") or ""
        # cheap extract of path-like tokens after common writers
        return re.findall(r"(?:^|[\s'\"])([\w./-]+\.[\w]+)", cmd)
    return []


def main() -> None:
    session = os.environ.get("KYZO_TASK_SESSION")
    if not session or not Path(session).is_file():
        sys.exit(0)
    data = json.loads(Path(session).read_text())
    allowlist = list(data.get("allowlist") or [])
    if not allowlist:
        sys.exit(0)

    payload = json.load(sys.stdin)
    tool = payload.get("tool_name") or payload.get("toolName") or ""
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    paths = _paths_from_input(tool, tool_input)
    offenders = [p for p in paths if p and not _covers(p, allowlist)]
    if not offenders:
        sys.exit(0)

    offenses = int(data.get("offenses") or 0) + 1
    data["offenses"] = offenses
    Path(session).write_text(json.dumps(data, indent=2) + "\n")
    reason = f"KYZO allowlist deny ({offenses}): {', '.join(offenders)}"
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    print(reason, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
