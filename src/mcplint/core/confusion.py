"""Cross-references the static ambiguity engine's predicted tool-pairs against
confusions actually observed in a benchmark run.

A pair is "confirmed" when the ambiguity engine flagged it and the model
also picked the wrong tool from that pair at least once. A pair is
"surprising" when the model confused two tools the ambiguity engine did not
flag: that is a signal the engine's heuristics are missing something, since
runtime behavior is ground truth.
"""

from __future__ import annotations

from itertools import combinations

from mcplint.core.rules.ambiguity import DEFAULT_AMBIGUITY_THRESHOLD, compute_ambiguity
from mcplint.models.benchmark import BenchmarkDataset, BenchmarkResult
from mcplint.models.common import ArtifactMetadata
from mcplint.models.confusion import CONFUSION_SCHEMA_VERSION, ConfusionAnalysis, ConfusionPair
from mcplint.models.snapshot import MCPServerSnapshot


def analyze_confusion(
    snapshot: MCPServerSnapshot,
    dataset: BenchmarkDataset,
    result: BenchmarkResult,
    *,
    ambiguity_threshold: float = DEFAULT_AMBIGUITY_THRESHOLD,
) -> ConfusionAnalysis:
    expected_tool_by_case = {case.id: case.expected.tool for case in dataset.cases}
    tool_names = {tool.name for tool in snapshot.tools}

    confusions: dict[frozenset[str], int] = {}
    relevant: dict[frozenset[str], int] = {}
    for trial in result.trials:
        expected_tool = expected_tool_by_case.get(trial.case_id)
        if expected_tool is None or expected_tool not in tool_names:
            continue

        for other_tool in tool_names - {expected_tool}:
            pair = frozenset({expected_tool, other_tool})
            relevant[pair] = relevant.get(pair, 0) + 1

        actual_tool = trial.actual.tool
        if actual_tool is None or actual_tool == expected_tool or actual_tool not in tool_names:
            continue
        pair = frozenset({expected_tool, actual_tool})
        confusions[pair] = confusions.get(pair, 0) + 1

    pairs: list[ConfusionPair] = []
    for tool_a, tool_b in combinations(sorted(tool_names), 2):
        pair_key = frozenset({tool_a, tool_b})
        ambiguity = compute_ambiguity(
            next(t for t in snapshot.tools if t.name == tool_a),
            next(t for t in snapshot.tools if t.name == tool_b),
        )
        predicted = ambiguity.score >= ambiguity_threshold
        observed_confusions = confusions.get(pair_key, 0)
        relevant_trials = relevant.get(pair_key, 0)
        if not predicted and observed_confusions == 0:
            continue
        observed_confusion_rate = observed_confusions / relevant_trials if relevant_trials else 0.0
        pairs.append(
            ConfusionPair(
                tool_a=tool_a,
                tool_b=tool_b,
                ambiguity_score=ambiguity.score,
                predicted=predicted,
                observed_confusions=observed_confusions,
                relevant_trials=relevant_trials,
                observed_confusion_rate=round(observed_confusion_rate, 4),
                confirmed=predicted and observed_confusions > 0,
                surprising=not predicted and observed_confusions > 0,
            )
        )

    pairs.sort(key=lambda p: (-p.observed_confusions, -p.ambiguity_score))

    return ConfusionAnalysis(
        metadata=ArtifactMetadata.create(schema_version=CONFUSION_SCHEMA_VERSION),
        dataset_name=dataset.name,
        ambiguity_threshold=ambiguity_threshold,
        pairs=pairs,
    )
