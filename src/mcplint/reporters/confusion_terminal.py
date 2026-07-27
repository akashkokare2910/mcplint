"""Render a ConfusionAnalysis as Rich-formatted terminal text."""

from __future__ import annotations

from io import StringIO

from rich.console import Console
from rich.table import Table

from mcplint.models.confusion import ConfusionAnalysis


def render_confusion_terminal(analysis: ConfusionAnalysis) -> str:
    buffer = StringIO()
    console = Console(file=buffer, width=140, record=True)

    console.print(
        f"[bold]{analysis.dataset_name}[/bold]: {len(analysis.pairs)} flagged pair(s), "
        f"ambiguity threshold {analysis.ambiguity_threshold:.2f}"
    )

    if not analysis.pairs:
        console.print(
            "[green]No pair was predicted ambiguous or observed confused in trials.[/green]"
        )
        return buffer.getvalue()

    table = Table()
    table.add_column("Tool A")
    table.add_column("Tool B")
    table.add_column("Ambiguity")
    table.add_column("Predicted")
    table.add_column("Observed")
    table.add_column("Rate")
    table.add_column("Verdict")
    for pair in analysis.pairs:
        if pair.confirmed:
            verdict_style, verdict_text = "bold red", "CONFIRMED"
        elif pair.surprising:
            verdict_style, verdict_text = "bold yellow", "SURPRISING"
        else:
            verdict_style, verdict_text = "dim", "predicted only"
        table.add_row(
            pair.tool_a,
            pair.tool_b,
            f"{pair.ambiguity_score:.2f}",
            "yes" if pair.predicted else "no",
            str(pair.observed_confusions),
            f"{pair.observed_confusion_rate:.0%}",
            f"[{verdict_style}]{verdict_text}[/{verdict_style}]",
        )
    console.print(table)

    return buffer.getvalue()
