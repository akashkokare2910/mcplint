"""`mcplint benchmark`: run a benchmark dataset against a live MCP server."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import anyio
import typer
from rich.console import Console

from mcplint.benchmark.dataset import DatasetError, load_dataset
from mcplint.benchmark.providers.factory import ProviderNotAvailableError, create_provider
from mcplint.benchmark.runner import run_benchmark
from mcplint.mcp_client.persistence import load_snapshot
from mcplint.mcp_client.session import collect_stdio_snapshot
from mcplint.mcp_client.stdio import parse_command
from mcplint.models.benchmark import BenchmarkResult
from mcplint.reporters.benchmark_terminal import render_benchmark_terminal

console = Console()
error_console = Console(stderr=True)


def benchmark_command(
    dataset_path: Annotated[Path, typer.Argument(help="Path to the benchmark dataset YAML.")],
    server: Annotated[
        str | None, typer.Option("--server", help="Command line to launch the MCP server.")
    ] = None,
    snapshot: Annotated[
        Path | None, typer.Option("--snapshot", help="Path to a saved snapshot JSON file.")
    ] = None,
    provider: Annotated[
        str, typer.Option("--provider", help="Benchmark provider: fake, anthropic, or openai.")
    ] = "fake",
    model: Annotated[
        str | None, typer.Option("--model", help="Model name for the provider.")
    ] = None,
    runs: Annotated[int, typer.Option("--runs", help="Trials per case.")] = 3,
    format: Annotated[str, typer.Option("--format", help="Output format.")] = "terminal",
    output: Annotated[
        Path | None, typer.Option("--output", help="Path to write the BenchmarkResult JSON to.")
    ] = None,
) -> None:
    if (server is None) == (snapshot is None):
        error_console.print(
            "[bold red]Exactly one of --server or --snapshot is required.[/bold red]"
        )
        raise typer.Exit(code=2)
    if format not in ("terminal", "json"):
        error_console.print(f"[bold red]Unknown format: {format}[/bold red]")
        raise typer.Exit(code=2)

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

    async def _run() -> BenchmarkResult:
        return await run_benchmark(dataset, server_snapshot.tools, chosen_provider, runs=runs)

    result = anyio.run(_run)

    if format == "json":
        console.print(result.model_dump_json(indent=2))
    else:
        console.print(render_benchmark_terminal(result))

    if output is not None:
        output.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
