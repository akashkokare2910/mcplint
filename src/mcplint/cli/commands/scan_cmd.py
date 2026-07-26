"""`mcplint scan` — lint a live MCP server or a saved snapshot."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import anyio
import typer
from rich.console import Console

from mcplint.core.engine import lint_snapshot
from mcplint.core.registry import RuleRegistry
from mcplint.mcp_client.persistence import load_snapshot
from mcplint.mcp_client.session import collect_stdio_snapshot
from mcplint.mcp_client.stdio import parse_command
from mcplint.models.findings import LintReport, Severity
from mcplint.reporters.json_reporter import render_json
from mcplint.reporters.terminal import render_terminal

console = Console()
error_console = Console(stderr=True)

_SEVERITY_RANK = {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}
_FAIL_ON_THRESHOLD = {
    "error": _SEVERITY_RANK[Severity.ERROR],
    "warning": _SEVERITY_RANK[Severity.WARNING],
}


def _should_fail(report: LintReport, fail_on: str) -> bool:
    if fail_on == "never":
        return False
    threshold = _FAIL_ON_THRESHOLD[fail_on]
    return any(_SEVERITY_RANK[finding.severity] >= threshold for finding in report.findings)


def scan_command(
    server: Annotated[
        str | None, typer.Option("--server", help="Command line to launch the MCP server.")
    ] = None,
    snapshot: Annotated[
        Path | None, typer.Option("--snapshot", help="Path to a saved snapshot JSON file.")
    ] = None,
    format: Annotated[str, typer.Option("--format", help="Output format.")] = "terminal",
    fail_on: Annotated[
        str, typer.Option("--fail-on", help="Minimum severity that fails the command.")
    ] = "error",
) -> None:
    if (server is None) == (snapshot is None):
        error_console.print(
            "[bold red]Exactly one of --server or --snapshot is required.[/bold red]"
        )
        raise typer.Exit(code=2)
    if format not in ("terminal", "json"):
        error_console.print(f"[bold red]Unknown format: {format}[/bold red]")
        raise typer.Exit(code=2)
    if fail_on not in ("error", "warning", "never"):
        error_console.print(f"[bold red]Unknown --fail-on: {fail_on}[/bold red]")
        raise typer.Exit(code=2)

    try:
        if snapshot is not None:
            server_snapshot = load_snapshot(snapshot)
        else:
            assert server is not None
            command, args = parse_command(server)
            server_snapshot = anyio.run(collect_stdio_snapshot, command, args)
    except Exception as exc:  # noqa: BLE001 - surfaced as a CI-friendly CLI error
        error_console.print(f"[bold red]Failed to load server contract:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    report = lint_snapshot(server_snapshot, RuleRegistry.with_builtin_rules())

    if format == "json":
        console.print(render_json(report))
    else:
        console.print(render_terminal(report))

    if _should_fail(report, fail_on):
        raise typer.Exit(code=1)
