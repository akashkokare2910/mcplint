from datetime import UTC, datetime

import pytest

from mcplint.compare.differ import (
    diff_ambiguity,
    diff_benchmarks,
    diff_findings,
    diff_tool_contracts,
    diff_tool_names,
)
from mcplint.core.engine import lint_snapshot
from mcplint.core.registry import RuleRegistry
from mcplint.models.benchmark import BenchmarkResult
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _tool(
    name: str, description: str | None, input_schema: dict[str, object] | None = None
) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description=description,
        input_schema=input_schema or {"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )


def _snapshot(name: str, *tools: ToolContract) -> MCPServerSnapshot:
    return MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name=name,
        server_version=None,
        transport="stdio",
        command=None,
        tools=list(tools),
    )


def test_diff_tool_names_added_and_removed() -> None:
    baseline = _snapshot("s", _tool("get_customer", "desc"), _tool("delete_customer", "desc"))
    candidate = _snapshot("s", _tool("get_customer", "desc"), _tool("search_customers", "desc"))
    added, removed = diff_tool_names(baseline, candidate)
    assert added == ["search_customers"]
    assert removed == ["delete_customer"]


def test_diff_tool_contracts_detects_description_and_schema_changes() -> None:
    baseline = _snapshot(
        "s", _tool("get_customer", "Old description.", {"type": "object", "properties": {}})
    )
    candidate = _snapshot(
        "s",
        _tool(
            "get_customer",
            "New description.",
            {"type": "object", "properties": {"id": {"type": "string"}}},
        ),
    )
    schema_changes, description_changes = diff_tool_contracts(baseline, candidate)
    assert len(schema_changes) == 1
    assert schema_changes[0].json_path == "$.inputSchema"
    assert len(description_changes) == 1
    assert description_changes[0].before == "Old description."
    assert description_changes[0].after == "New description."


def test_diff_findings_new_and_resolved() -> None:
    baseline_snapshot = _snapshot("s", _tool("get_customer", None))
    candidate_snapshot = _snapshot(
        "s",
        _tool(
            "get_customer",
            "Retrieve a single customer record by its exact customer identifier. "
            "Returns the customer's profile fields as JSON. Raises an error if "
            "the identifier does not exist.",
        ),
    )
    registry = RuleRegistry.with_builtin_rules()
    baseline_report = lint_snapshot(baseline_snapshot, registry)
    candidate_report = lint_snapshot(candidate_snapshot, registry)

    new_findings, resolved_findings = diff_findings(baseline_report, candidate_report)
    assert new_findings == []
    assert any(f.rule_id == "missing-tool-description" for f in resolved_findings)


def test_diff_ambiguity_detects_score_change() -> None:
    baseline = _snapshot(
        "s", _tool("get_customer", "Get a thing."), _tool("search_customer", "Search a thing.")
    )
    candidate = _snapshot(
        "s",
        _tool("get_customer", "Get a thing."),
        _tool(
            "search_customer",
            "Retrieve customers by browsing a completely unrelated catalog of products.",
        ),
    )
    changes = diff_ambiguity(baseline, candidate)
    assert len(changes) == 1
    assert changes[0].tool_a == "get_customer"
    assert changes[0].tool_b == "search_customer"
    assert changes[0].before != changes[0].after


def _benchmark_result(
    accuracy: float,
    valid_rate: float,
    latency: float,
    cost: float | None,
    per_case: dict[str, float],
) -> BenchmarkResult:
    return BenchmarkResult(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        dataset_name="customer-tools",
        provider="fake",
        model="fake-model",
        runs_per_case=1,
        trials=[],
        exact_tool_selection_accuracy=accuracy,
        valid_argument_rate=valid_rate,
        required_argument_accuracy=1.0,
        forbidden_tool_invocation_rate=0.0,
        no_tool_rate=0.0,
        mean_latency_ms=latency,
        p95_latency_ms=latency,
        total_estimated_cost=cost,
        per_case_pass_rate=per_case,
        stability={case_id: 1.0 for case_id in per_case},
    )


def test_diff_benchmarks_computes_deltas_and_regressions() -> None:
    baseline = _benchmark_result(0.9, 0.95, 100.0, 0.01, {"c1": 1.0, "c2": 1.0})
    candidate = _benchmark_result(0.8, 0.90, 150.0, 0.02, {"c1": 1.0, "c2": 0.5})

    deltas = diff_benchmarks(baseline, candidate)
    assert deltas["benchmark_accuracy_delta"] == pytest.approx(-0.1)
    assert deltas["argument_validity_delta"] == pytest.approx(-0.05)
    assert deltas["latency_delta_ms"] == pytest.approx(50.0)
    assert deltas["cost_delta"] == pytest.approx(0.01)
    assert "c2" in deltas["regressions_by_case"]
    assert "c1" not in deltas["regressions_by_case"]
