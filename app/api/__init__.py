"""API: the transport edge. The one FastMCP server this whole program serves. Constructing this
package is what mounts everything: the instance is built first, then each surface module is imported
for the registration its `@mcp.tool` decorators perform — the reason `main.py` only needs
`from app.api import mcp`, already fully populated with every tool."""

from fastmcp import FastMCP

mcp = FastMCP("board")

# ruff: noqa: E402  (imports must follow `mcp`'s construction, which they mount onto)
from app.api import board  # pyright: ignore[reportUnusedImport]  — registers the board tools
