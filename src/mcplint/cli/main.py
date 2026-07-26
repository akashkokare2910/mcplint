"""MCPLint CLI entrypoint."""

from __future__ import annotations

import typer

from mcplint.cli.commands.inspect_cmd import inspect_command
from mcplint.cli.commands.rules_cmd import rules_command
from mcplint.cli.commands.scan_cmd import scan_command
from mcplint.cli.commands.snapshot_cmd import snapshot_command

app = typer.Typer(name="mcplint", help="ESLint for MCP tool contracts.")


@app.callback()
def _callback() -> None:
    """ESLint for MCP tool contracts."""


app.command("inspect")(inspect_command)
app.command("snapshot")(snapshot_command)
app.command("scan")(scan_command)
app.command("rules")(rules_command)


if __name__ == "__main__":
    app()
