from mcplint.benchmark.providers.base import ProviderResult
from mcplint.benchmark.scorer import (
    aggregate_metrics,
    make_trial,
    score_trial,
    to_actual_tool_call,
    validate_arguments,
)
from mcplint.models.benchmark import ActualToolCall, ExpectedToolCall
from mcplint.models.contracts import ToolAnnotation, ToolContract


def _tool(name: str, required: list[str], properties: dict[str, object]) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description="desc",
        input_schema={"type": "object", "properties": properties, "required": required},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )


def test_validate_arguments_valid() -> None:
    tools = [_tool("get_customer", ["customer_id"], {"customer_id": {"type": "string"}})]
    assert validate_arguments("get_customer", {"customer_id": "1042"}, tools) is True


def test_validate_arguments_missing_required() -> None:
    tools = [_tool("get_customer", ["customer_id"], {"customer_id": {"type": "string"}})]
    assert validate_arguments("get_customer", {}, tools) is False


def test_validate_arguments_unknown_tool() -> None:
    tools = [_tool("get_customer", [], {})]
    assert validate_arguments("delete_customer", {}, tools) is False


def test_validate_arguments_no_tool_selected() -> None:
    tools = [_tool("get_customer", [], {})]
    assert validate_arguments(None, {}, tools) is False


def test_score_trial_exact_match_passes() -> None:
    expected = ExpectedToolCall(tool="get_customer", arguments={"customer_id": "1042"})
    actual = ActualToolCall(
        tool="get_customer", arguments={"customer_id": "1042"}, valid_arguments=True
    )
    passed, reasons = score_trial(expected, actual)
    assert passed is True
    assert reasons == []


def test_score_trial_wrong_tool_fails() -> None:
    expected = ExpectedToolCall(tool="get_customer")
    actual = ActualToolCall(tool="search_customers", valid_arguments=True)
    passed, reasons = score_trial(expected, actual)
    assert passed is False
    assert any("expected tool" in r for r in reasons)


def test_score_trial_forbidden_tool_fails() -> None:
    expected = ExpectedToolCall(tool="get_customer", forbidden_tools=["delete_customer"])
    actual = ActualToolCall(tool="delete_customer", valid_arguments=True)
    passed, reasons = score_trial(expected, actual)
    assert passed is False
    assert any("forbidden" in r for r in reasons)


def test_score_trial_no_tool_fails() -> None:
    expected = ExpectedToolCall(tool="get_customer")
    actual = ActualToolCall(tool=None, valid_arguments=False)
    passed, reasons = score_trial(expected, actual)
    assert passed is False
    assert any("no tool" in r for r in reasons)


def test_score_trial_argument_mismatch_fails() -> None:
    expected = ExpectedToolCall(tool="search_customers", argument_assertions={"status": "active"})
    actual = ActualToolCall(
        tool="search_customers", arguments={"status": "inactive"}, valid_arguments=True
    )
    passed, reasons = score_trial(expected, actual)
    assert passed is False
    assert any("status" in r for r in reasons)


def test_to_actual_tool_call_maps_provider_result() -> None:
    tools = [_tool("get_customer", ["customer_id"], {"customer_id": {"type": "string"}})]
    result = ProviderResult(
        tool="get_customer", arguments={"customer_id": "1042"}, latency_ms=120.5
    )
    actual = to_actual_tool_call(result, tools)
    assert actual.valid_arguments is True
    assert actual.latency_ms == 120.5


def test_aggregate_metrics_computes_accuracy_and_rates() -> None:
    expected_by_case = {
        "c1": ExpectedToolCall(tool="get_customer", forbidden_tools=["delete_customer"]),
    }
    trials = [
        make_trial(
            "c1",
            0,
            expected_by_case["c1"],
            ActualToolCall(tool="get_customer", valid_arguments=True),
        ),
        make_trial(
            "c1",
            1,
            expected_by_case["c1"],
            ActualToolCall(tool="delete_customer", valid_arguments=True),
        ),
    ]
    metrics = aggregate_metrics(trials, expected_by_case)
    assert metrics["exact_tool_selection_accuracy"] == 0.5
    assert metrics["forbidden_tool_invocation_rate"] == 0.5
    assert metrics["per_case_pass_rate"]["c1"] == 0.5
    assert metrics["stability"]["c1"] == 0.5
