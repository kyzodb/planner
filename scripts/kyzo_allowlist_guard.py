#!/usr/bin/env python3
"""PreToolUse: deny Read/Edit/Write outside KYZO allowlist; deny git when armed.

Expects env KYZO_TASK_SESSION pointing at a JSON file:
  {"allowlist": ["path/or/glob", ...], "offenses": 0}

Reads Claude Code hook JSON from stdin. Denies with exit 2 when path is off-list
or when Bash invokes git. No session file → allow (orchestrator has not armed a task).
"""

from __future__ import annotations

import json
import os
import re
import sys
from fnmatch import fnmatch
from pathlib import Path

_GIT_CMD = re.compile(r"(^|[\s;&|])git([\s]|$)")


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


def _bash_invokes_git(tool: str, tool_input: dict) -> bool:
    if tool != "Bash":
        return False
    cmd = tool_input.get("command") or ""
    return bool(_GIT_CMD.search(cmd))


def _deny(session_path: Path, data: dict, reason: str) -> None:
    offenses = int(data.get("offenses") or 0) + 1
    data["offenses"] = offenses
    session_path.write_text(json.dumps(data, indent=2) + "\n")
    full = f"KYZO allowlist deny ({offenses}): {reason}"
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "permissionDecision": "deny",
                    "permissionDecisionReason": full,
                }
            }
        )
    )
    print(full, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    session = os.environ.get("KYZO_TASK_SESSION")
    if not session or not Path(session).is_file():
        sys.exit(0)
    session_path = Path(session)
    data = json.loads(session_path.read_text())
    allowlist = list(data.get("allowlist") or [])
    if not allowlist:
        sys.exit(0)

    payload = json.load(sys.stdin)
    tool = payload.get("tool_name") or payload.get("toolName") or ""
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}

    # Armed session: git is never an allowlisted task action (verify/parent own git).
    if _bash_invokes_git(tool, tool_input):
        _deny(session_path, data, "git is denied while KYZO_TASK_SESSION is armed")

    paths = _paths_from_input(tool, tool_input)
    offenders = [p for p in paths if p and not _covers(p, allowlist)]
    if not offenders:
        sys.exit(0)

    _deny(session_path, data, ", ".join(offenders))


if __name__ == "__main__":
    main()
