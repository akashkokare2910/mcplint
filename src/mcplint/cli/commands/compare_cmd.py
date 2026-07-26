"""`mcplint compare` — diff two snapshots and optionally re-run a benchmark against both."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import anyio
import typer
from rich.console import Console

from mcplint.benchmark.dataset import DatasetError, load_dataset
from mcplint.benchmark.providers.factory import ProviderNotAvailableError, create_provider
from mcplint.benchmark.runner import run_benchmark
from mcplint.compare.differ import (
    diff_ambiguity,
    diff_benchmarks,
    diff_findings,
    diff_tool_contracts,
    diff_tool_names,
)
from mcplint.core.engine import lint_snapshot
from mcplint.core.registry import RuleRegistry
from mcplint.mcp_client.persistence import load_snapshot
from mcplint.models.common import ArtifactMetadata
from mcplint.models.comparison import ComparisonReport
from mcplint.reporters.comparison_terminal import render_comparison_terminal

console = Console()
error_console = Console(stderr=True)

COMPARISON_SCHEMA_VERSION = "1.0"


def compare_command(
    baseline: Annotated[Path, typer.Option("--baseline", help="Baseline snapshot JSON path.")],
    candidate: Annotated[Path, typer.Option("--candidate", help="Candidate snapshot JSON path.")],
    dataset_path: Annotated[
        Path | None,
        typer.Option("--dataset", help="Benchmark dataset YAML to re-run against both."),
    ] = None,
    provider: Annotated[str, typer.Option("--provider", help="Benchmark provider.")] = "fake",
    model: Annotated[
        str | None, typer.Option("--model", help="Model name for the provider.")
    ] = None,
    runs: Annotated[int, typer.Option("--runs", help="Trials per case.")] = 3,
    min_accuracy_delta: Annotated[
        float | None,
        typer.Option("--min-accuracy-delta", help="Fail if accuracy delta falls below this."),
    ] = None,
    format: Annotated[str, typer.Option("--format", help="Output format.")] = "terminal",
    output: Annotated[
        Path | None, typer.Option("--output", help="Path to write the ComparisonReport JSON to.")
    ] = None,
) -> None:
    if format not in ("terminal", "json"):
        error_console.print(f"[bold red]Unknown format: {format}[/bold red]")
        raise typer.Exit(code=2)

    try:
        baseline_snapshot = load_snapshot(baseline)
        candidate_snapshot = load_snapshot(candidate)
    except FileNotFoundError as exc:
        error_console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=2) from exc

    registry = RuleRegistry.with_builtin_rules()
    baseline_report = lint_snapshot(baseline_snapshot, registry)
    candidate_report = lint_snapshot(candidate_snapshot, registry)

    added_tools, removed_tools = diff_tool_names(baseline_snapshot, candidate_snapshot)
    schema_changes, description_changes = diff_tool_contracts(baseline_snapshot, candidate_snapshot)
    new_findings, resolved_findings = diff_findings(baseline_report, candidate_report)
    ambiguity_changes = diff_ambiguity(baseline_snapshot, candidate_snapshot)

    report = ComparisonReport(
        metadata=ArtifactMetadata.create(schema_version=COMPARISON_SCHEMA_VERSION),
        baseline_server_name=baseline_snapshot.server_name,
        candidate_server_name=candidate_snapshot.server_name,
        added_tools=added_tools,
        removed_tools=removed_tools,
        schema_changes=schema_changes,
        description_changes=description_changes,
        new_findings=new_findings,
        resolved_findings=resolved_findings,
        ambiguity_score_changes=ambiguity_changes,
        min_accuracy_delta_threshold=min_accuracy_delta,
    )

    if dataset_path is not None:
        try:
            dataset = load_dataset(dataset_path)
        except DatasetError as exc:
            error_console.print(f"[bold red]{exc}[/bold red]")
            raise typer.Exit(code=2) from exc
        try:
            chosen_provider = create_provider(provider, model)
        except ProviderNotAvailableError as exc:
            error_console.print(f"[bold red]{exc}[/bold red]")
            raise typer.Exit(code=2) from exc

        async def _run_both() -> tuple[object, object]:
            baseline_result = await run_benchmark(
                dataset, baseline_snapshot.tools, chosen_provider, runs=runs
            )
            candidate_result = await run_benchmark(
                dataset, candidate_snapshot.tools, chosen_provider, runs=runs
            )
            return baseline_result, candidate_result

        baseline_result, candidate_result = anyio.run(_run_both)
        deltas = diff_benchmarks(baseline_result, candidate_result)  # type: ignore[arg-type]

        report = report.model_copy(
            update={
                "benchmark_dataset_name": dataset.name,
                "baseline_accuracy": baseline_result.exact_tool_selection_accuracy,  # type: ignore[attr-defined]
                "candidate_accuracy": candidate_result.exact_tool_selection_accuracy,  # type: ignore[attr-defined]
                **deltas,
            }
        )
        if min_accuracy_delta is not None:
            accuracy_delta = deltas["benchmark_accuracy_delta"]
            assert isinstance(accuracy_delta, float)
            report = report.model_copy(
                update={"passes_ci_threshold": accuracy_delta >= min_accuracy_delta}
            )

    if format == "json":
        console.print(report.model_dump_json(indent=2))
    else:
        console.print(render_comparison_terminal(report))

    if output is not None:
        output.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")

    if report.passes_ci_threshold is False:
        raise typer.Exit(code=1)
