"""Render a BenchmarkResult as Rich-formatted terminal text."""

from __future__ import annotations

from io import StringIO

from rich.console import Console
from rich.table import Table

from mcplint.models.benchmark import BenchmarkResult


def render_benchmark_terminal(result: BenchmarkResult) -> str:
    buffer = StringIO()
    console = Console(file=buffer, width=140, record=True)

    console.print(
        f"[bold]{result.dataset_name}[/bold] via {result.provider}/{result.model} "
        f"({result.runs_per_case} runs/case, {len(result.trials)} trials total)"
    )

    metrics = Table(title="Metrics")
    metrics.add_column("Metric")
    metrics.add_column("Value", justify="right")
    metrics.add_row("Exact tool-selection accuracy", f"{result.exact_tool_selection_accuracy:.2%}")
    metrics.add_row("Valid-argument rate", f"{result.valid_argument_rate:.2%}")
    metrics.add_row("Required-argument accuracy", f"{result.required_argument_accuracy:.2%}")
    metrics.add_row(
        "Forbidden-tool invocation rate", f"{result.forbidden_tool_invocation_rate:.2%}"
    )
    metrics.add_row("No-tool rate", f"{result.no_tool_rate:.2%}")
    metrics.add_row("Mean latency", f"{result.mean_latency_ms:.1f} ms")
    metrics.add_row("P95 latency", f"{result.p95_latency_ms:.1f} ms")
    if result.total_estimated_cost is not None:
        metrics.add_row("Total estimated cost", f"${result.total_estimated_cost:.4f}")
    console.print(metrics)

    per_case = Table(title="Per-case results")
    per_case.add_column("Case")
    per_case.add_column("Pass rate", justify="right")
    per_case.add_column("Stability", justify="right")
    for case_id, pass_rate in result.per_case_pass_rate.items():
        per_case.add_row(case_id, f"{pass_rate:.2%}", f"{result.stability.get(case_id, 0.0):.2%}")
    console.print(per_case)

    return buffer.getvalue()
