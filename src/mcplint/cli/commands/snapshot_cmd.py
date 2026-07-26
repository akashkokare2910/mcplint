"""`mcplint snapshot` — connect to an MCP server and persist its contract as JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import anyio
import typer
from rich.console import Console

from mcplint.mcp_client.persistence import save_snapshot
from mcplint.mcp_client.session import collect_stdio_snapshot
from mcplint.mcp_client.stdio import parse_command

console = Console()
error_console = Console(stderr=True)


def snapshot_command(
    server: Annotated[str, typer.Option("--server", help="Command line to launch the MCP server.")],
    output: Annotated[Path, typer.Option("--output", help="Path to write the snapshot JSON to.")],
) -> None:
    command, args = parse_command(server)

    try:
        snapshot = anyio.run(collect_stdio_snapshot, command, args)
    except Exception as exc:  # noqa: BLE001 - surfaced as a CI-friendly CLI error
        error_console.print(f"[bold red]Failed to snapshot server:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    save_snapshot(snapshot, output)
    console.print(f"[green]Wrote snapshot for {snapshot.server_name} to {output}[/green]")
