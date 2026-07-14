"""Entrypoint. Importing `app.api` builds the one `board` server and mounts the board tool surface;
running it serves the work-board tools over MCP.

The server root (`mcp/`) is placed on `sys.path` so `app` resolves no matter how this file is
launched."""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the mcp/ server root
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.api import mcp  # noqa: E402  (must follow the sys.path shim above)

if __name__ == "__main__":
    mcp.run()
