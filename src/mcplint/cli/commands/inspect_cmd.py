"""`mcplint inspect`: connect to an MCP server and print its tool contracts."""

from __future__ import annotations

from typing import Annotated

import anyio
import typer
from rich.console import Console
from rich.table import Table

from mcplint.mcp_client.session import collect_stdio_snapshot
from mcplint.mcp_client.stdio import parse_command

console = Console()
error_console = Console(stderr=True)


def inspect_command(
    server: Annotated[str, typer.Option("--server", help="Command line to launch the MCP server.")],
) -> None:
    command, args = parse_command(server)

    try:
        snapshot = anyio.run(collect_stdio_snapshot, command, args)
    except Exception as exc:  # noqa: BLE001 - surfaced as a CI-friendly CLI error
        error_console.print(f"[bold red]Failed to inspect server:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Tools on {snapshot.server_name}")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Params", justify="right")
    table.add_column("Destructive", justify="center")

    for tool in snapshot.tools:
        table.add_row(
            tool.name,
            tool.description or "[dim](none)[/dim]",
            str(len(tool.parameters)),
            "yes" if tool.annotations.destructive_hint else "",
        )

    console.print(table)
