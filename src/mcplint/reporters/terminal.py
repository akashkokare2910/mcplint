"""Render a LintReport as Rich-formatted terminal text."""

from __future__ import annotations

from io import StringIO

from rich.console import Console
from rich.table import Table

from mcplint.models.findings import LintReport, Severity

_SEVERITY_STYLE = {Severity.ERROR: "bold red", Severity.WARNING: "yellow", Severity.INFO: "cyan"}


def render_terminal(report: LintReport) -> str:
    buffer = StringIO()
    console = Console(file=buffer, width=120, record=True)

    counts = report.count_by_severity()
    console.print(
        f"[bold]{report.server_name}[/bold] — "
        f"{len(report.findings)} finding(s) "
        f"({counts.get(Severity.ERROR, 0)} error, "
        f"{counts.get(Severity.WARNING, 0)} warning, "
        f"{counts.get(Severity.INFO, 0)} info)"
    )

    if report.findings:
        table = Table()
        table.add_column("Rule")
        table.add_column("Severity")
        table.add_column("Tool")
        table.add_column("Message")
        table.add_column("Confidence", justify="right")
        for finding in report.findings:
            style = _SEVERITY_STYLE[finding.severity]
            table.add_row(
                finding.rule_id,
                f"[{style}]{finding.severity.value}[/{style}]",
                finding.location.tool_name,
                finding.message,
                f"{finding.confidence:.2f}",
            )
        console.print(table)

    return buffer.getvalue()
