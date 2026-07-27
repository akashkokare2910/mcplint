"""Render a MutationTestingReport as Rich-formatted terminal text."""

from __future__ import annotations

from io import StringIO

from rich.console import Console
from rich.table import Table

from mcplint.models.mutation import MutationTestingReport


def render_mutation_terminal(report: MutationTestingReport) -> str:
    buffer = StringIO()
    console = Console(file=buffer, width=140, record=True)

    console.print(
        f"[bold]{report.dataset_name}[/bold]: {len(report.results)} mutation(s) tested, "
        f"kill threshold {report.kill_threshold:.0%}, "
        f"survival rate {report.survival_rate:.0%}"
    )

    if not report.results:
        console.print("[yellow]No mutators were applicable to this snapshot.[/yellow]")
        return buffer.getvalue()

    table = Table()
    table.add_column("Mutator")
    table.add_column("Tool")
    table.add_column("Baseline")
    table.add_column("Mutated")
    table.add_column("Drop")
    table.add_column("Verdict")
    for result in report.results:
        verdict_style = "green" if result.killed else "bold red"
        verdict_text = "killed" if result.killed else "SURVIVED"
        table.add_row(
            result.mutator_id,
            result.tool_name,
            f"{result.baseline_accuracy:.0%}",
            f"{result.mutated_accuracy:.0%}",
            f"{result.accuracy_drop:+.0%}",
            f"[{verdict_style}]{verdict_text}[/{verdict_style}]",
        )
    console.print(table)

    return buffer.getvalue()
