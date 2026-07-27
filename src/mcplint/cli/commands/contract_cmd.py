"""`mcplint contract` — the ContractLab command group.

Behavioral contract validation, adversarial benchmark generation, and
mutation testing all operate on the same pair of inputs: a
`mcplint.contract.yaml` and an `MCPServerSnapshot` (from `--server` or
`--snapshot`, same as `scan`/`benchmark`/`compare`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import anyio
import typer
import yaml
from rich.console import Console

from mcplint.benchmark.adversarial import generate_adversarial_dataset
from mcplint.benchmark.dataset import DatasetError, load_dataset
from mcplint.benchmark.providers.factory import ProviderNotAvailableError, create_provider
from mcplint.contract.loader import ContractError, load_contract
from mcplint.contract.validator import validate_contract_against_snapshot
from mcplint.mcp_client.persistence import load_snapshot
from mcplint.mcp_client.session import collect_stdio_snapshot
from mcplint.mcp_client.stdio import parse_command
from mcplint.models.snapshot import MCPServerSnapshot
from mcplint.mutation.engine import DEFAULT_KILL_THRESHOLD, run_mutation_testing
from mcplint.reporters.contract_terminal import render_contract_validation_terminal
from mcplint.reporters.mutation_terminal import render_mutation_terminal

app = typer.Typer(
    name="contract", help="Behavioral contracts: validate, generate-benchmark, mutate."
)

console = Console()
error_console = Console(stderr=True)


def _resolve_snapshot(server: str | None, snapshot: Path | None) -> MCPServerSnapshot:
    if (server is None) == (snapshot is None):
        error_console.print(
            "[bold red]Exactly one of --server or --snapshot is required.[/bold red]"
        )
        raise typer.Exit(code=2)
    try:
        if snapshot is not None:
            return load_snapshot(snapshot)
        assert server is not None
        command, args = parse_command(server)
        return anyio.run(collect_stdio_snapshot, command, args)
    except Exception as exc:  # noqa: BLE001 - surfaced as a CI-friendly CLI error
        error_console.print(f"[bold red]Failed to load server contract:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command("validate")
def validate_command(
    contract_path: Annotated[Path, typer.Argument(help="Path to mcplint.contract.yaml.")],
    server: Annotated[
        str | None, typer.Option("--server", help="Command line to launch the MCP server.")
    ] = None,
    snapshot: Annotated[
        Path | None, typer.Option("--snapshot", help="Path to a saved snapshot JSON file.")
    ] = None,
) -> None:
    try:
        contract = load_contract(contract_path)
    except ContractError as exc:
        error_console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=2) from exc

    server_snapshot = _resolve_snapshot(server, snapshot)
    issues = validate_contract_against_snapshot(contract, server_snapshot)
    console.print(render_contract_validation_terminal(contract.name, issues))

    if issues:
        raise typer.Exit(code=1)


@app.command("generate-benchmark")
def generate_benchmark_command(
    contract_path: Annotated[Path, typer.Argument(help="Path to mcplint.contract.yaml.")],
    server: Annotated[
        str | None, typer.Option("--server", help="Command line to launch the MCP server.")
    ] = None,
    snapshot: Annotated[
        Path | None, typer.Option("--snapshot", help="Path to a saved snapshot JSON file.")
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", help="Path to write the generated benchmark dataset YAML to."),
    ] = Path("adversarial.evals.yaml"),
) -> None:
    try:
        contract = load_contract(contract_path)
    except ContractError as exc:
        error_console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=2) from exc

    server_snapshot = _resolve_snapshot(server, snapshot)

    issues = validate_contract_against_snapshot(contract, server_snapshot)
    for issue in issues:
        error_console.print(
            f"[yellow]Warning:[/yellow] {issue.tool_name}: {issue.message} "
            "(skipping any case that would depend on it)"
        )

    dataset = generate_adversarial_dataset(contract, server_snapshot)
    if not dataset.cases:
        error_console.print(
            "[yellow]No 'prefer_over' entries produced a usable case "
            "(check the contract has at least one, and both tools exist in the snapshot).[/yellow]"
        )

    dataset_yaml = yaml.safe_dump(dataset.model_dump(mode="json"), sort_keys=False)
    output.write_text(dataset_yaml, encoding="utf-8")
    console.print(f"[green]Generated {len(dataset.cases)} adversarial case(s) to {output}[/green]")


@app.command("mutate")
def mutate_command(
    contract_path: Annotated[Path, typer.Argument(help="Path to mcplint.contract.yaml.")],
    dataset_path: Annotated[Path, typer.Option("--dataset", help="Benchmark dataset YAML.")],
    server: Annotated[
        str | None, typer.Option("--server", help="Command line to launch the MCP server.")
    ] = None,
    snapshot: Annotated[
        Path | None, typer.Option("--snapshot", help="Path to a saved snapshot JSON file.")
    ] = None,
    provider: Annotated[str, typer.Option("--provider", help="Benchmark provider.")] = "fake",
    model: Annotated[
        str | None, typer.Option("--model", help="Model name for the provider.")
    ] = None,
    runs: Annotated[int, typer.Option("--runs", help="Trials per case, per run.")] = 3,
    kill_threshold: Annotated[
        float,
        typer.Option(
            "--kill-threshold", help="Minimum accuracy drop for a mutation to count as killed."
        ),
    ] = DEFAULT_KILL_THRESHOLD,
    min_kill_rate: Annotated[
        float | None,
        typer.Option(
            "--min-kill-rate", help="Fail if the fraction of killed mutations falls below this."
        ),
    ] = None,
) -> None:
    try:
        contract = load_contract(contract_path)
    except ContractError as exc:
        error_console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=2) from exc

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

    server_snapshot = _resolve_snapshot(server, snapshot)

    report = anyio.run(
        lambda: run_mutation_testing(
            server_snapshot,
            dataset,
            chosen_provider,
            runs=runs,
            kill_threshold=kill_threshold,
            only_tool_names=contract.tool_names(),
        )
    )
    console.print(render_mutation_terminal(report))

    if min_kill_rate is not None:
        kill_rate = 1.0 - report.survival_rate
        if kill_rate < min_kill_rate:
            error_console.print(
                f"[bold red]Kill rate {kill_rate:.0%} is below --min-kill-rate "
                f"{min_kill_rate:.0%}.[/bold red]"
            )
            raise typer.Exit(code=1)
