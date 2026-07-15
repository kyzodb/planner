#!/usr/bin/env python3
"""Write .kyzo/task-session.json for hooks + orchestrator. Args: allowlist paths..."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: kyzo_arm_session.py <path-or-glob>...", file=sys.stderr)
        sys.exit(2)
    root = Path.cwd() / ".kyzo"
    root.mkdir(exist_ok=True)
    session = root / "task-session.json"
    payload = {"allowlist": sys.argv[1:], "offenses": 0, "edits": 0, "idle_tools": 0}
    session.write_text(json.dumps(payload, indent=2) + "\n")
    print(session)


if __name__ == "__main__":
    main()
