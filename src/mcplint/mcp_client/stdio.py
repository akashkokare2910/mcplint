"""Process-spawning helpers for stdio MCP servers.

MCP servers invoked here are treated as untrusted local processes: the
command/args are passed as a list (never shell=True) and no output beyond
the MCP protocol stream is trusted or persisted.
"""

from __future__ import annotations

import shlex


def parse_command(command_line: str) -> tuple[str, list[str]]:
    parts = shlex.split(command_line)
    if not parts:
        raise ValueError("Empty server command")
    return parts[0], parts[1:]
