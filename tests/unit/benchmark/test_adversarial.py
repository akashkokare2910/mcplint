from datetime import UTC, datetime

from mcplint.benchmark.adversarial import generate_adversarial_dataset
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contract import BehavioralContract, PreferOverRule, ToolBehavior, ToolIntent
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _intent(**overrides: str) -> ToolIntent:
    defaults = {
        "operation": "read",
        "cardinality": "one",
        "matching": "exact",
        "side_effects": "none",
        "risk": "low",
    }
    defaults.update(overrides)
    return ToolIntent(**defaults)


def _tool(name: str) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description="desc",
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


def test_generate_adversarial_dataset_one_case_per_prefer_over_entry() -> None:
    contract = BehavioralContract(
        schema_version="1",
        name="customer-server",
        tools={
            "get_customer": ToolBehavior(
                intent=_intent(),
                prefer_over={
                    "search_customers": PreferOverRule(
                        when="A known immutable customer ID is supplied."
                    )
                },
            ),
            "search_customers": ToolBehavior(
                intent=_intent(cardinality="many", matching="partial"),
                prefer_over={
                    "get_customer": PreferOverRule(when="The exact customer ID is unknown.")
                },
            ),
        },
    )
    snapshot = _snapshot(_tool("get_customer"), _tool("search_customers"))

    dataset = generate_adversarial_dataset(contract, snapshot)

    assert dataset.name == "customer-server-adversarial"
    assert len(dataset.cases) == 2
    case_ids = {c.id for c in dataset.cases}
    assert case_ids == {
        "prefer-get_customer-over-search_customers",
        "prefer-search_customers-over-get_customer",
    }

    get_customer_case = next(
        c for c in dataset.cases if c.id == "prefer-get_customer-over-search_customers"
    )
    assert get_customer_case.expected.tool == "get_customer"
    assert get_customer_case.expected.forbidden_tools == ["search_customers"]
    assert "known immutable customer ID" in get_customer_case.prompt
    assert "get_customer" in get_customer_case.prompt
    assert "search_customers" in get_customer_case.prompt


def test_generate_adversarial_dataset_skips_tools_missing_from_snapshot() -> None:
    contract = BehavioralContract(
        schema_version="1",
        name="s",
        tools={
            "get_customer": ToolBehavior(
                intent=_intent(),
                prefer_over={"search_customers": PreferOverRule(when="x")},
            ),
        },
    )
    # search_customers is not in the snapshot: the pair must be skipped.
    dataset = generate_adversarial_dataset(contract, _snapshot(_tool("get_customer")))
    assert dataset.cases == []


def test_generate_adversarial_dataset_no_prefer_over_yields_no_cases() -> None:
    contract = BehavioralContract(
        schema_version="1",
        name="s",
        tools={"get_customer": ToolBehavior(intent=_intent())},
    )
    dataset = generate_adversarial_dataset(contract, _snapshot(_tool("get_customer")))
    assert dataset.cases == []
