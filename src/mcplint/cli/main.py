"""MCPLint CLI entrypoint."""

from __future__ import annotations

from typing import Annotated

import typer

from mcplint.__about__ import __version__
from mcplint.cli.commands.benchmark_cmd import benchmark_command
from mcplint.cli.commands.compare_cmd import compare_command
from mcplint.cli.commands.confusion_cmd import confusion_command
from mcplint.cli.commands.contract_cmd import app as contract_app
from mcplint.cli.commands.fix_cmd import fix_command
from mcplint.cli.commands.inspect_cmd import inspect_command
from mcplint.cli.commands.rules_cmd import rules_command
from mcplint.cli.commands.scan_cmd import scan_command
from mcplint.cli.commands.snapshot_cmd import snapshot_command

app = typer.Typer(name="mcplint", help="ESLint for MCP tool contracts.")


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"mcplint {__version__}")
        raise typer.Exit


@app.callback()
def _callback(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_print_version, is_eager=True, help="Print the version and exit."
        ),
    ] = False,
) -> None:
    """ESLint for MCP tool contracts."""


app.command("inspect")(inspect_command)
app.command("snapshot")(snapshot_command)
app.command("scan")(scan_command)
app.command("rules")(rules_command)
app.command("benchmark")(benchmark_command)
app.command("compare")(compare_command)
app.command("fix")(fix_command)
app.command("confusion")(confusion_command)
app.add_typer(contract_app)


if __name__ == "__main__":
    app()
