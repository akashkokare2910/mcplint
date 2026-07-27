from datetime import UTC, datetime

import pytest

from mcplint.benchmark.providers.base import ProviderResult
from mcplint.benchmark.providers.fake import FakeProvider
from mcplint.models.benchmark import BenchmarkCase, BenchmarkDataset, ExpectedToolCall
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot
from mcplint.mutation.engine import apply_mutation, run_mutation_testing
from mcplint.mutation.mutators import StripDistinctionLanguageMutator, TruncateToVagueMutator


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
            BenchmarkCase(
                id="c1",
                prompt="Look up the exact customer.",
                expected=ExpectedToolCall(
                    tool="get_customer", forbidden_tools=["search_customers"]
                ),
            )
        ],
    )


def test_apply_mutation_only_changes_the_targeted_tool() -> None:
    get_customer = _tool("get_customer", "Retrieve a customer by its exact ID.")
    search_customers = _tool("search_customers", "Search for customers.")
    snapshot = _snapshot(get_customer, search_customers)

    mutated = apply_mutation(snapshot, TruncateToVagueMutator(), "get_customer")

    assert mutated.get_tool("get_customer").description == "Retrieve a"
    assert mutated.get_tool("search_customers").description == "Search for customers."
    # original snapshot is untouched
    assert snapshot.get_tool("get_customer").description == "Retrieve a customer by its exact ID."


@pytest.mark.asyncio
async def test_run_mutation_testing_detects_a_killed_mutation() -> None:
    get_customer = _tool(
        "get_customer", "Retrieve a customer by its exact ID. Use search_customers otherwise."
    )
    search_customers = _tool("search_customers", "Search for customers.")
    snapshot = _snapshot(get_customer, search_customers)

    def responder(prompt: str, tools: list[ToolContract]) -> ProviderResult:
        for tool in tools:
            if tool.description and "exact" in tool.description.lower():
                return ProviderResult(tool=tool.name)
        return ProviderResult(tool="search_customers")

    provider = FakeProvider(model="m", responder=responder)
    report = await run_mutation_testing(
        snapshot,
        _dataset(),
        provider,
        runs=1,
        mutators=[StripDistinctionLanguageMutator()],
    )

    assert len(report.results) == 1
    result = report.results[0]
    assert result.mutator_id == "strip-distinction-language"
    assert result.tool_name == "get_customer"
    assert result.baseline_accuracy == 1.0
    assert result.mutated_accuracy == 0.0
    assert result.killed is True
    assert report.survival_rate == 0.0


@pytest.mark.asyncio
async def test_run_mutation_testing_detects_a_survived_mutation() -> None:
    get_customer = _tool(
        "get_customer", "Retrieve a customer by its exact ID. Use search_customers otherwise."
    )
    search_customers = _tool("search_customers", "Search for customers.")
    snapshot = _snapshot(get_customer, search_customers)

    # This responder always picks the right tool by case prompt alone,
    # ignoring description content entirely: description mutations can
    # never change its answer, so every mutation should survive.
    def responder(prompt: str, tools: list[ToolContract]) -> ProviderResult:
        return ProviderResult(tool="get_customer")

    provider = FakeProvider(model="m", responder=responder)
    report = await run_mutation_testing(
        snapshot,
        _dataset(),
        provider,
        runs=1,
        mutators=[StripDistinctionLanguageMutator()],
    )

    assert len(report.results) == 1
    result = report.results[0]
    assert result.accuracy_drop == 0.0
    assert result.killed is False
    assert report.survival_rate == 1.0


@pytest.mark.asyncio
async def test_run_mutation_testing_skips_inapplicable_mutators() -> None:
    # A two-word description: TruncateToVagueMutator does not apply
    # (requires > 3 words), so no result should be produced for it.
    get_customer = _tool("get_customer", "Gets data.")
    snapshot = _snapshot(get_customer)

    provider = FakeProvider(model="m", responder=lambda p, t: ProviderResult(tool="get_customer"))
    dataset = BenchmarkDataset(
        name="d",
        version="1",
        cases=[BenchmarkCase(id="c1", prompt="p", expected=ExpectedToolCall(tool="get_customer"))],
    )

    report = await run_mutation_testing(
        snapshot, dataset, provider, runs=1, mutators=[TruncateToVagueMutator()]
    )

    assert report.results == []
    assert report.survival_rate == 0.0


@pytest.mark.asyncio
async def test_run_mutation_testing_respects_only_tool_names() -> None:
    get_customer = _tool("get_customer", "Retrieve a customer by its exact ID.")
    search_customers = _tool("search_customers", "Search for many customers here.")
    snapshot = _snapshot(get_customer, search_customers)
    provider = FakeProvider(model="m", responder=lambda p, t: ProviderResult(tool="get_customer"))

    report = await run_mutation_testing(
        snapshot,
        _dataset(),
        provider,
        runs=1,
        mutators=[TruncateToVagueMutator()],
        only_tool_names={"search_customers"},
    )

    tool_names_mutated = {result.tool_name for result in report.results}
    assert tool_names_mutated == {"search_customers"}
