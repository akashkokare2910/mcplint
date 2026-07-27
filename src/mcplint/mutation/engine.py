"""Runs mutation testing: applies each applicable mutator to each tool,
re-runs the benchmark against the mutated snapshot, and compares accuracy
against a baseline run.

Reuses `run_benchmark` unchanged for both the baseline and every mutated
run, and applies the same "accuracy drop >= threshold" kill criterion as
`compare --min-accuracy-delta`, just inverted (a mutation should hurt
accuracy; failing to do so is the finding).
"""

from __future__ import annotations

from mcplint.benchmark.providers.base import ToolCallingProvider
from mcplint.benchmark.runner import run_benchmark
from mcplint.models.benchmark import BenchmarkDataset
from mcplint.models.common import ArtifactMetadata
from mcplint.models.mutation import (
    MUTATION_REPORT_SCHEMA_VERSION,
    MutationResult,
    MutationTestingReport,
)
from mcplint.models.snapshot import MCPServerSnapshot
from mcplint.mutation.mutators import MUTATORS, Mutator

DEFAULT_KILL_THRESHOLD = 0.05


def apply_mutation(
    snapshot: MCPServerSnapshot, mutator: Mutator, tool_name: str
) -> MCPServerSnapshot:
    mutated_tools = [
        mutator.mutate(tool) if tool.name == tool_name else tool for tool in snapshot.tools
    ]
    return snapshot.model_copy(update={"tools": mutated_tools})


async def run_mutation_testing(
    snapshot: MCPServerSnapshot,
    dataset: BenchmarkDataset,
    provider: ToolCallingProvider,
    *,
    runs: int = 3,
    kill_threshold: float = DEFAULT_KILL_THRESHOLD,
    mutators: list[Mutator] | None = None,
    only_tool_names: set[str] | None = None,
) -> MutationTestingReport:
    """`only_tool_names` restricts which tools get mutated (e.g. to those
    covered by a behavioral contract) without changing which tools the
    provider sees: every run still passes the full, unfiltered tool list.
    """
    active_mutators = mutators if mutators is not None else [cls() for cls in MUTATORS]

    baseline = await run_benchmark(dataset, snapshot.tools, provider, runs=runs)
    baseline_accuracy = baseline.exact_tool_selection_accuracy

    results: list[MutationResult] = []
    for tool in snapshot.tools:
        if only_tool_names is not None and tool.name not in only_tool_names:
            continue
        for mutator in active_mutators:
            if not mutator.applies_to(tool):
                continue

            mutated_snapshot = apply_mutation(snapshot, mutator, tool.name)
            mutated_result = await run_benchmark(
                dataset, mutated_snapshot.tools, provider, runs=runs
            )
            mutated_accuracy = mutated_result.exact_tool_selection_accuracy
            accuracy_drop = baseline_accuracy - mutated_accuracy

            results.append(
                MutationResult(
                    mutator_id=mutator.id,
                    tool_name=tool.name,
                    baseline_accuracy=baseline_accuracy,
                    mutated_accuracy=mutated_accuracy,
                    accuracy_drop=accuracy_drop,
                    killed=accuracy_drop >= kill_threshold,
                )
            )

    survived = sum(1 for result in results if not result.killed)
    survival_rate = survived / len(results) if results else 0.0

    return MutationTestingReport(
        metadata=ArtifactMetadata.create(schema_version=MUTATION_REPORT_SCHEMA_VERSION),
        dataset_name=dataset.name,
        kill_threshold=kill_threshold,
        results=results,
        survival_rate=survival_rate,
    )
