from datetime import UTC, datetime

from mcplint.core.confusion import analyze_confusion
from mcplint.models.benchmark import (
    ActualToolCall,
    BenchmarkCase,
    BenchmarkDataset,
    BenchmarkResult,
    BenchmarkTrial,
    ExpectedToolCall,
)
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _tool(name: str, description: str) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description=description,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )


def _snapshot(*tools: ToolContract) -> MCPServerSnapshot:
    return MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="s",
        server_version=None,
        transport="stdio",
        command=None,
        tools=list(tools),
    )


def _dataset() -> BenchmarkDataset:
    return BenchmarkDataset(
        name="d",
        version="1",
        cases=[
            BenchmarkCase(id="c1", prompt="p1", expected=ExpectedToolCall(tool="get_customer")),
            BenchmarkCase(id="c2", prompt="p2", expected=ExpectedToolCall(tool="get_customer")),
        ],
    )


def _result(*, actual_tools: list[str | None]) -> BenchmarkResult:
    trials = [
        BenchmarkTrial(
            case_id=f"c{i + 1}",
            trial_index=0,
            actual=ActualToolCall(tool=actual_tool),
            passed=actual_tool == "get_customer",
        )
        for i, actual_tool in enumerate(actual_tools)
    ]
    return BenchmarkResult(
        metadata=ArtifactMetadata.create(schema_version="1.0"),
        dataset_name="d",
        provider="fake",
        model="fake-echo-model",
        runs_per_case=1,
        trials=trials,
        exact_tool_selection_accuracy=0.0,
        valid_argument_rate=1.0,
        required_argument_accuracy=1.0,
        forbidden_tool_invocation_rate=0.0,
        no_tool_rate=0.0,
        mean_latency_ms=0.0,
        p95_latency_ms=0.0,
        total_estimated_cost=None,
        per_case_pass_rate={},
        stability={},
    )


def test_confirmed_pair_flagged_when_predicted_and_observed() -> None:
    get_customer = _tool("get_customer", "Retrieve a customer.")
    search_customers = _tool("search_customers", "Retrieve a customer by search.")
    snapshot = _snapshot(get_customer, search_customers)
    result = _result(actual_tools=["search_customers", "search_customers"])

    analysis = analyze_confusion(snapshot, _dataset(), result, ambiguity_threshold=0.1)

    assert len(analysis.pairs) == 1
    pair = analysis.pairs[0]
    assert {pair.tool_a, pair.tool_b} == {"get_customer", "search_customers"}
    assert pair.predicted is True
    assert pair.observed_confusions == 2
    assert pair.relevant_trials == 2
    assert pair.observed_confusion_rate == 1.0
    assert pair.confirmed is True
    assert pair.surprising is False


def test_surprising_pair_flagged_when_observed_but_not_predicted() -> None:
    get_customer = _tool("get_customer", "Retrieve a customer by exact ID.")
    delete_customer = _tool("delete_customer", "Permanently remove an account record.")
    snapshot = _snapshot(get_customer, delete_customer)
    result = _result(actual_tools=["delete_customer", "get_customer"])

    analysis = analyze_confusion(snapshot, _dataset(), result, ambiguity_threshold=0.9)

    assert len(analysis.pairs) == 1
    pair = analysis.pairs[0]
    assert pair.predicted is False
    assert pair.observed_confusions == 1
    assert pair.confirmed is False
    assert pair.surprising is True


def test_pair_omitted_when_neither_predicted_nor_observed() -> None:
    get_customer = _tool("get_customer", "Retrieve a customer by exact ID.")
    delete_customer = _tool("delete_customer", "Permanently remove an account record.")
    snapshot = _snapshot(get_customer, delete_customer)
    result = _result(actual_tools=["get_customer", "get_customer"])

    analysis = analyze_confusion(snapshot, _dataset(), result, ambiguity_threshold=0.9)

    assert analysis.pairs == []


def test_predicted_only_pair_has_zero_observed_confusions() -> None:
    get_customer = _tool("get_customer", "Retrieve a customer.")
    search_customers = _tool("search_customers", "Retrieve a customer by search.")
    snapshot = _snapshot(get_customer, search_customers)
    result = _result(actual_tools=["get_customer", "get_customer"])

    analysis = analyze_confusion(snapshot, _dataset(), result, ambiguity_threshold=0.1)

    assert len(analysis.pairs) == 1
    pair = analysis.pairs[0]
    assert pair.predicted is True
    assert pair.observed_confusions == 0
    assert pair.confirmed is False
    assert pair.surprising is False
