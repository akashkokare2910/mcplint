"""Render a ComparisonReport as Rich-formatted terminal text."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from mcplint.models.comparison import ComparisonReport


def render_comparison_terminal(report: ComparisonReport) -> str:
    buffer = StringIO()
    console = Console(file=buffer, width=140, record=True)

    console.print(
        f"[bold]{report.baseline_server_name}[/bold] -> "
        f"[bold]{report.candidate_server_name}[/bold]"
    )

    if report.added_tools:
        console.print(f"[green]Added tools:[/green] {', '.join(report.added_tools)}")
    if report.removed_tools:
        console.print(f"[red]Removed tools:[/red] {', '.join(report.removed_tools)}")
    if report.description_changes:
        console.print(f"Description changes: {len(report.description_changes)}")
    if report.schema_changes:
        console.print(f"Schema changes: {len(report.schema_changes)}")

    console.print(
        f"Findings: [red]{len(report.new_findings)} new[/red], "
        f"[green]{len(report.resolved_findings)} resolved[/green]"
    )

    if report.ambiguity_score_changes:
        console.print(f"Ambiguity score changes: {len(report.ambiguity_score_changes)}")
        for change in report.ambiguity_score_changes:
            direction = "up" if change.after > change.before else "down"
            console.print(
                f"  {change.tool_a} <-> {change.tool_b}: "
                f"{change.before:.2f} -> {change.after:.2f} ({direction})"
            )

    if report.benchmark_dataset_name is not None:
        console.print(f"\n[bold]Benchmark: {report.benchmark_dataset_name}[/bold]")
        console.print(
            f"  Accuracy: {report.baseline_accuracy:.2%} -> {report.candidate_accuracy:.2%} "
            f"(delta {report.benchmark_accuracy_delta:+.2%})"
        )
        if report.regressions_by_case:
            console.print("  [red]Regressions:[/red]")
            for case_id, description in report.regressions_by_case.items():
                console.print(f"    {case_id}: {description}")
        if report.min_accuracy_delta_threshold is not None:
            verdict = "PASS" if report.passes_ci_threshold else "FAIL"
            style = "green" if report.passes_ci_threshold else "bold red"
            console.print(
                f"  CI threshold (--min-accuracy-delta "
                f"{report.min_accuracy_delta_threshold:+.2%}): [{style}]{verdict}[/{style}]"
            )

    return buffer.getvalue()
