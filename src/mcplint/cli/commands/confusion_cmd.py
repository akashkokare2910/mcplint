"""`mcplint confusion`: cross-reference the static ambiguity engine against
tool confusions actually observed in a benchmark run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console

from mcplint.benchmark.dataset import DatasetError, load_dataset
from mcplint.core.confusion import analyze_confusion
from mcplint.core.rules.ambiguity import DEFAULT_AMBIGUITY_THRESHOLD
from mcplint.mcp_client.persistence import load_snapshot
from mcplint.models.benchmark import BenchmarkResult
from mcplint.reporters.confusion_terminal import render_confusion_terminal

console = Console()
error_console = Console(stderr=True)


def confusion_command(
    result_path: Annotated[
        Path, typer.Option("--result", help="Path to a saved BenchmarkResult JSON file.")
    ],
    dataset_path: Annotated[
        Path, typer.Option("--dataset", help="Benchmark dataset YAML the result was run from.")
    ],
    snapshot: Annotated[
        Path, typer.Option("--snapshot", help="Path to a saved snapshot JSON file.")
    ],
    threshold: Annotated[
        float,
        typer.Option("--threshold", help="Ambiguity score at or above which a pair is flagged."),
    ] = DEFAULT_AMBIGUITY_THRESHOLD,
    format: Annotated[str, typer.Option("--format", help="Output format.")] = "terminal",
    output: Annotated[
        Path | None, typer.Option("--output", help="Path to write the ConfusionAnalysis JSON to.")
    ] = None,
    fail_on_surprising: Annotated[
        bool,
        typer.Option(
            "--fail-on-surprising",
            help="Exit non-zero if any tool pair was confused but not predicted ambiguous.",
        ),
    ] = False,
) -> None:
    if format not in ("terminal", "json"):
        error_console.print(f"[bold red]Unknown format: {format}[/bold red]")
        raise typer.Exit(code=2)

    try:
        dataset = load_dataset(dataset_path)
    except DatasetError as exc:
        error_console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=2) from exc

    try:
        server_snapshot = load_snapshot(snapshot)
    except FileNotFoundError as exc:
        error_console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=2) from exc

    try:
        result = BenchmarkResult.model_validate(json.loads(result_path.read_text()))
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as exc:
        error_console.print(f"[bold red]Failed to load benchmark result:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    analysis = analyze_confusion(server_snapshot, dataset, result, ambiguity_threshold=threshold)

    if format == "json":
        console.print(analysis.model_dump_json(indent=2))
    else:
        console.print(render_confusion_terminal(analysis))

    if output is not None:
        output.write_text(analysis.model_dump_json(indent=2) + "\n", encoding="utf-8")

    if fail_on_surprising and any(pair.surprising for pair in analysis.pairs):
        raise typer.Exit(code=1)
