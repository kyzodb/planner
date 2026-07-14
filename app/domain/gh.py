"""The one place `gh` the subprocess is spawned. Every foreign lift (a model's own `.fetch`
classmethod) and every causal route call passes through `run` and nothing else. No domain meaning
is decided here; this file names no type and computes no fact."""

import json
import subprocess


def run(*args: str, stdin: str | None = None) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, input=stdin)
    if proc.returncode != 0:
        raise RuntimeError(f"gh {args[0]}: {proc.stderr.strip()}")
    return proc.stdout


def graphql(query: str, **fields: str | None) -> dict:
    """Run a GraphQL query and return its validated `data`. `gh` exits 0 even for GraphQL-level
    failures (rate limit, malformed query) — returning an `errors` array with null `data` — so this
    refuses those loudly instead of letting a `data[...]` chain die on `None`. A field whose value is
    None (an absent pagination cursor) is omitted."""
    args = ["api", "graphql", "-f", f"query={query}"]
    for key, value in fields.items():
        if value is not None:
            args += ["-F", f"{key}={value}"]
    reply = json.loads(run(*args))
    if reply.get("errors"):
        raise RuntimeError(f"graphql errors: {reply['errors']}")
    data = reply.get("data")
    if data is None:
        raise RuntimeError("graphql returned null data with no errors — unexpected response shape")
    return data
