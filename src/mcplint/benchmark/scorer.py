"""Deterministic scoring of benchmark trials. No LLM judge: every metric here
is computed from exact tool-name/argument comparison and JSON Schema validation.
"""

from __future__ import annotations

import jsonschema

from mcplint.benchmark.providers.base import ProviderResult
from mcplint.models.benchmark import ActualToolCall, BenchmarkTrial, ExpectedToolCall
from mcplint.models.contracts import ToolContract

BENCHMARK_RESULT_SCHEMA_VERSION = "1.0"


def validate_arguments(
    tool_name: str | None, arguments: dict[str, object], tools: list[ToolContract]
) -> bool:
    if tool_name is None:
        return False
    tool = next((t for t in tools if t.name == tool_name), None)
    if tool is None:
        return False
    try:
        jsonschema.validate(instance=arguments, schema=tool.input_schema)
    except jsonschema.ValidationError:
        return False
    return True


def to_actual_tool_call(result: ProviderResult, tools: list[ToolContract]) -> ActualToolCall:
    return ActualToolCall(
        tool=result.tool,
        arguments=result.arguments,
        valid_arguments=validate_arguments(result.tool, result.arguments, tools),
        error=result.error,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        estimated_cost=result.estimated_cost,
    )


def score_trial(expected: ExpectedToolCall, actual: ActualToolCall) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if actual.tool is None:
        reasons.append("no tool was selected")
    elif actual.tool != expected.tool:
        reasons.append(f"expected tool '{expected.tool}', got '{actual.tool}'")

    if actual.tool is not None and actual.tool in expected.forbidden_tools:
        reasons.append(f"invoked forbidden tool '{actual.tool}'")

    if not actual.valid_arguments:
        reasons.append("arguments do not validate against the tool's input schema")

    for key, expected_value in expected.all_expected_arguments().items():
        actual_value = actual.arguments.get(key)
        if actual_value != expected_value:
            reasons.append(f"argument '{key}': expected {expected_value!r}, got {actual_value!r}")

    return (not reasons, reasons)


def make_trial(
    case_id: str, trial_index: int, expected: ExpectedToolCall, actual: ActualToolCall
) -> BenchmarkTrial:
    passed, reasons = score_trial(expected, actual)
    return BenchmarkTrial(
        case_id=case_id,
        trial_index=trial_index,
        actual=actual,
        passed=passed,
        failure_reasons=reasons,
    )


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(percentile * (len(ordered) - 1))))
    return ordered[index]


def aggregate_metrics(
    trials: list[BenchmarkTrial],
    expected_by_case: dict[str, ExpectedToolCall],
) -> dict[str, object]:
    total = len(trials)
    exact_matches = sum(1 for t in trials if t.actual.tool == expected_by_case[t.case_id].tool)
    valid_args = sum(1 for t in trials if t.actual.valid_arguments)
    forbidden = sum(
        1 for t in trials if t.actual.tool in expected_by_case[t.case_id].forbidden_tools
    )
    no_tool = sum(1 for t in trials if t.actual.tool is None)

    required_correct = 0
    required_total = 0
    for trial in trials:
        expected = expected_by_case[trial.case_id]
        if trial.actual.tool != expected.tool:
            continue
        required_total += 1
        expected_args = expected.all_expected_arguments()
        if all(trial.actual.arguments.get(k) == v for k, v in expected_args.items()):
            required_correct += 1

    latencies = [t.actual.latency_ms for t in trials]
    costs = [t.actual.estimated_cost for t in trials if t.actual.estimated_cost is not None]

    per_case_pass_rate: dict[str, float] = {}
    stability: dict[str, float] = {}
    by_case: dict[str, list[BenchmarkTrial]] = {}
    for trial in trials:
        by_case.setdefault(trial.case_id, []).append(trial)
    for case_id, case_trials in by_case.items():
        passed_count = sum(1 for t in case_trials if t.passed)
        per_case_pass_rate[case_id] = passed_count / len(case_trials)
        majority = max(passed_count, len(case_trials) - passed_count)
        stability[case_id] = majority / len(case_trials)

    return {
        "exact_tool_selection_accuracy": exact_matches / total if total else 0.0,
        "valid_argument_rate": valid_args / total if total else 0.0,
        "required_argument_accuracy": (
            required_correct / required_total if required_total else 0.0
        ),
        "forbidden_tool_invocation_rate": forbidden / total if total else 0.0,
        "no_tool_rate": no_tool / total if total else 0.0,
        "mean_latency_ms": sum(latencies) / total if total else 0.0,
        "p95_latency_ms": _percentile(latencies, 0.95),
        "total_estimated_cost": sum(costs) if costs else None,
        "per_case_pass_rate": per_case_pass_rate,
        "stability": stability,
    }


__all__ = [
    "BENCHMARK_RESULT_SCHEMA_VERSION",
    "aggregate_metrics",
    "make_trial",
    "score_trial",
    "to_actual_tool_call",
    "validate_arguments",
]
