"""MCPLint CLI entrypoint."""

from __future__ import annotations

import typer

from mcplint.cli.commands.inspect_cmd import inspect_command

app = typer.Typer(name="mcplint", help="ESLint for MCP tool contracts.")


@app.callback()
def _callback() -> None:
    """ESLint for MCP tool contracts."""


app.command("inspect")(inspect_command)


if __name__ == "__main__":
    app()
