import pytest

from mcplint.benchmark.providers.base import ProviderResult
from mcplint.benchmark.providers.fake import FakeProvider
from mcplint.benchmark.runner import run_benchmark
from mcplint.models.benchmark import BenchmarkCase, BenchmarkDataset, ExpectedToolCall
from mcplint.models.contracts import ToolAnnotation, ToolContract


def _tool(name: str) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description="desc",
        input_schema={
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )


@pytest.mark.asyncio
async def test_run_benchmark_always_correct_provider() -> None:
    dataset = BenchmarkDataset(
        name="customer-tools",
        version="1",
        cases=[
            BenchmarkCase(
                id="exact-lookup",
                prompt="Retrieve customer 1042.",
                expected=ExpectedToolCall(tool="get_customer", arguments={"customer_id": "1042"}),
            )
        ],
    )
    tools = [_tool("get_customer"), _tool("delete_customer")]

    def responder(prompt: str, tools: list[ToolContract]) -> ProviderResult:
        return ProviderResult(
            tool="get_customer", arguments={"customer_id": "1042"}, latency_ms=10.0
        )

    provider = FakeProvider(model="fake-model", responder=responder)
    result = await run_benchmark(dataset, tools, provider, runs=3)

    assert result.provider == "fake"
    assert result.model == "fake-model"
    assert result.runs_per_case == 3
    assert len(result.trials) == 3
    assert result.exact_tool_selection_accuracy == 1.0
    assert result.valid_argument_rate == 1.0


@pytest.mark.asyncio
async def test_run_benchmark_always_wrong_provider() -> None:
    dataset = BenchmarkDataset(
        name="customer-tools",
        version="1",
        cases=[
            BenchmarkCase(
                id="exact-lookup",
                prompt="Retrieve customer 1042.",
                expected=ExpectedToolCall(tool="get_customer", forbidden_tools=["delete_customer"]),
            )
        ],
    )
    tools = [_tool("get_customer"), _tool("delete_customer")]

    def responder(prompt: str, tools: list[ToolContract]) -> ProviderResult:
        return ProviderResult(
            tool="delete_customer", arguments={"customer_id": "1042"}, latency_ms=10.0
        )

    provider = FakeProvider(model="fake-model", responder=responder)
    result = await run_benchmark(dataset, tools, provider, runs=2)

    assert result.exact_tool_selection_accuracy == 0.0
    assert result.forbidden_tool_invocation_rate == 1.0
    assert all(not trial.passed for trial in result.trials)
