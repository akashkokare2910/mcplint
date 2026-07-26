"""Pure diff functions between two snapshots, lint reports, and benchmark results."""

from __future__ import annotations

from mcplint.core.rules.ambiguity import compute_ambiguity
from mcplint.models.benchmark import BenchmarkResult
from mcplint.models.comparison import AmbiguityScoreChange, DescriptionChange, SchemaChange
from mcplint.models.findings import Finding, LintReport
from mcplint.models.snapshot import MCPServerSnapshot

_FLOAT_EPSILON = 1e-9


def diff_tool_names(
    baseline: MCPServerSnapshot, candidate: MCPServerSnapshot
) -> tuple[list[str], list[str]]:
    baseline_names = {tool.name for tool in baseline.tools}
    candidate_names = {tool.name for tool in candidate.tools}
    added = sorted(candidate_names - baseline_names)
    removed = sorted(baseline_names - candidate_names)
    return added, removed


def diff_tool_contracts(
    baseline: MCPServerSnapshot, candidate: MCPServerSnapshot
) -> tuple[list[SchemaChange], list[DescriptionChange]]:
    baseline_names = {tool.name for tool in baseline.tools}
    candidate_names = {tool.name for tool in candidate.tools}
    common = sorted(baseline_names & candidate_names)

    schema_changes: list[SchemaChange] = []
    description_changes: list[DescriptionChange] = []

    for name in common:
        before_tool = baseline.get_tool(name)
        after_tool = candidate.get_tool(name)
        assert before_tool is not None and after_tool is not None

        if before_tool.description != after_tool.description:
            description_changes.append(
                DescriptionChange(
                    tool_name=name, before=before_tool.description, after=after_tool.description
                )
            )
        if before_tool.input_schema != after_tool.input_schema:
            schema_changes.append(
                SchemaChange(
                    tool_name=name,
                    json_path="$.inputSchema",
                    before=before_tool.input_schema,
                    after=after_tool.input_schema,
                )
            )
        if before_tool.output_schema != after_tool.output_schema:
            schema_changes.append(
                SchemaChange(
                    tool_name=name,
                    json_path="$.outputSchema",
                    before=before_tool.output_schema,
                    after=after_tool.output_schema,
                )
            )

    return schema_changes, description_changes


def _finding_key(finding: Finding) -> tuple[str, str, str, str]:
    return (
        finding.rule_id,
        finding.location.tool_name,
        finding.location.json_path,
        finding.message,
    )


def diff_findings(
    baseline_report: LintReport, candidate_report: LintReport
) -> tuple[list[Finding], list[Finding]]:
    baseline_keys = {_finding_key(f) for f in baseline_report.findings}
    candidate_keys = {_finding_key(f) for f in candidate_report.findings}

    new_findings = [f for f in candidate_report.findings if _finding_key(f) not in baseline_keys]
    resolved_findings = [
        f for f in baseline_report.findings if _finding_key(f) not in candidate_keys
    ]
    return new_findings, resolved_findings


def diff_ambiguity(
    baseline: MCPServerSnapshot, candidate: MCPServerSnapshot
) -> list[AmbiguityScoreChange]:
    baseline_names = {tool.name for tool in baseline.tools}
    candidate_names = {tool.name for tool in candidate.tools}
    common = sorted(baseline_names & candidate_names)

    changes: list[AmbiguityScoreChange] = []
    for index, name_a in enumerate(common):
        for name_b in common[index + 1 :]:
            baseline_a, baseline_b = baseline.get_tool(name_a), baseline.get_tool(name_b)
            candidate_a, candidate_b = candidate.get_tool(name_a), candidate.get_tool(name_b)
            assert baseline_a is not None and baseline_b is not None
            assert candidate_a is not None and candidate_b is not None

            before_score = compute_ambiguity(baseline_a, baseline_b).score
            after_score = compute_ambiguity(candidate_a, candidate_b).score
            if abs(before_score - after_score) > _FLOAT_EPSILON:
                changes.append(
                    AmbiguityScoreChange(
                        tool_a=name_a, tool_b=name_b, before=before_score, after=after_score
                    )
                )
    return changes


def diff_benchmarks(
    baseline_result: BenchmarkResult, candidate_result: BenchmarkResult
) -> dict[str, object]:
    baseline_accuracy = baseline_result.exact_tool_selection_accuracy
    candidate_accuracy = candidate_result.exact_tool_selection_accuracy
    accuracy_delta = candidate_accuracy - baseline_accuracy
    argument_validity_delta = (
        candidate_result.valid_argument_rate - baseline_result.valid_argument_rate
    )
    latency_delta_ms = candidate_result.mean_latency_ms - baseline_result.mean_latency_ms

    baseline_cost = baseline_result.total_estimated_cost
    candidate_cost = candidate_result.total_estimated_cost
    cost_delta: float | None = None
    if baseline_cost is not None or candidate_cost is not None:
        cost_delta = (candidate_cost or 0.0) - (baseline_cost or 0.0)

    regressions_by_case: dict[str, str] = {}
    baseline_cases = set(baseline_result.per_case_pass_rate)
    candidate_cases = set(candidate_result.per_case_pass_rate)
    common_cases = baseline_cases & candidate_cases
    for case_id in sorted(common_cases):
        before_rate = baseline_result.per_case_pass_rate[case_id]
        after_rate = candidate_result.per_case_pass_rate[case_id]
        if before_rate > after_rate:
            regressions_by_case[case_id] = f"pass rate {before_rate:.0%} -> {after_rate:.0%}"

    return {
        "benchmark_accuracy_delta": accuracy_delta,
        "argument_validity_delta": argument_validity_delta,
        "latency_delta_ms": latency_delta_ms,
        "cost_delta": cost_delta,
        "regressions_by_case": regressions_by_case,
    }
