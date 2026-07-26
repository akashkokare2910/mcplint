"""Runs a benchmark dataset against a provider and a fixed set of tools."""

from __future__ import annotations

from mcplint.benchmark.providers.base import ToolCallingProvider
from mcplint.benchmark.scorer import (
    BENCHMARK_RESULT_SCHEMA_VERSION,
    aggregate_metrics,
    make_trial,
    to_actual_tool_call,
)
from mcplint.models.benchmark import BenchmarkDataset, BenchmarkResult, BenchmarkTrial
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolContract


async def run_benchmark(
    dataset: BenchmarkDataset,
    tools: list[ToolContract],
    provider: ToolCallingProvider,
    *,
    runs: int = 3,
) -> BenchmarkResult:
    trials: list[BenchmarkTrial] = []
    expected_by_case = {case.id: case.expected for case in dataset.cases}

    for case in dataset.cases:
        for trial_index in range(runs):
            result = await provider.run(case.prompt, tools)
            actual = to_actual_tool_call(result, tools)
            trials.append(make_trial(case.id, trial_index, case.expected, actual))

    metrics = aggregate_metrics(trials, expected_by_case)

    return BenchmarkResult(
        metadata=ArtifactMetadata.create(schema_version=BENCHMARK_RESULT_SCHEMA_VERSION),
        dataset_name=dataset.name,
        provider=provider.name,
        model=provider.model,
        runs_per_case=runs,
        trials=trials,
        **metrics,
    )
