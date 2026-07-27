"""`mcplint fix`: propose deterministic rewrite suggestions as a Markdown patch report.

Never writes to the MCP server's source files. Only ever writes the patch
report itself, and only when --output is given.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from mcplint.core.engine import lint_snapshot
from mcplint.core.registry import RuleRegistry
from mcplint.fix.suggest import build_suggestions
from mcplint.mcp_client.persistence import load_snapshot
from mcplint.reporters.fix_markdown import render_fix_markdown

console = Console()
error_console = Console(stderr=True)


def fix_command(
    snapshot: Annotated[
        Path, typer.Option("--snapshot", help="Path to a saved snapshot JSON file.")
    ],
    llm_provider: Annotated[
        str | None,
        typer.Option(
            "--llm-provider",
            help="Enable LLM-assisted rewriting via this provider (not yet available).",
        ),
    ] = None,
    output: Annotated[
        Path | None, typer.Option("--output", help="Path to write the Markdown patch report to.")
    ] = None,
) -> None:
    if llm_provider is not None:
        error_console.print(
            "[bold red]LLM-assisted rewriting is not implemented yet.[/bold red] "
            "Omit --llm-provider to use deterministic suggestions only."
        )
        raise typer.Exit(code=2)

    try:
        server_snapshot = load_snapshot(snapshot)
    except FileNotFoundError as exc:
        error_console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=2) from exc

    report = lint_snapshot(server_snapshot, RuleRegistry.with_builtin_rules())
    suggestions = build_suggestions(server_snapshot, report)
    markdown = render_fix_markdown(server_snapshot.server_name, suggestions)

    console.print(markdown)

    if output is not None:
        output.write_text(markdown, encoding="utf-8")
