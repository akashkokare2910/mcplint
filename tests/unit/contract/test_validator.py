from datetime import UTC, datetime

from mcplint.contract.validator import validate_contract_against_snapshot
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contract import (
    BehavioralContract,
    PreferOverRule,
    ToolBehavior,
    ToolIntent,
)
from mcplint.models.contracts import ParameterContract, ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _read_intent() -> ToolIntent:
    return ToolIntent(
        operation="read", cardinality="one", matching="exact", side_effects="none", risk="low"
    )


def _tool(name: str, parameters: list[ParameterContract] | None = None) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description="desc",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=parameters or [],
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


def test_validate_passes_for_consistent_contract() -> None:
    tool = _tool(
        "get_customer",
        parameters=[
            ParameterContract(name="customer_id", json_schema={"type": "string"}, required=True)
        ],
    )
    other = _tool("search_customers")
    contract = BehavioralContract(
        schema_version="1",
        name="s",
        tools={
            "get_customer": ToolBehavior(
                intent=_read_intent(),
                requires=["customer_id"],
                prefer_over={"search_customers": PreferOverRule(when="exact id known")},
            ),
            "search_customers": ToolBehavior(intent=_read_intent()),
        },
    )
    issues = validate_contract_against_snapshot(contract, _snapshot(tool, other))
    assert issues == []


def test_validate_flags_unknown_tool() -> None:
    contract = BehavioralContract(
        schema_version="1",
        name="s",
        tools={"delete_customer": ToolBehavior(intent=_read_intent())},
    )
    issues = validate_contract_against_snapshot(contract, _snapshot())
    assert len(issues) == 1
    assert "does not exist" in issues[0].message


def test_validate_flags_unknown_required_parameter() -> None:
    tool = _tool("get_customer")
    contract = BehavioralContract(
        schema_version="1",
        name="s",
        tools={
            "get_customer": ToolBehavior(intent=_read_intent(), requires=["customer_id"]),
        },
    )
    issues = validate_contract_against_snapshot(contract, _snapshot(tool))
    assert len(issues) == 1
    assert "customer_id" in issues[0].message


def test_validate_flags_prefer_over_target_missing_from_snapshot() -> None:
    tool = _tool("get_customer")
    contract = BehavioralContract(
        schema_version="1",
        name="s",
        tools={
            "get_customer": ToolBehavior(
                intent=_read_intent(),
                prefer_over={"search_customers": PreferOverRule(when="x")},
            ),
        },
    )
    issues = validate_contract_against_snapshot(contract, _snapshot(tool))
    assert len(issues) == 1
    assert "search_customers" in issues[0].message
    assert "does not exist" in issues[0].message


def test_validate_flags_prefer_over_target_missing_from_contract() -> None:
    get_customer = _tool("get_customer")
    search_customers = _tool("search_customers")
    contract = BehavioralContract(
        schema_version="1",
        name="s",
        tools={
            "get_customer": ToolBehavior(
                intent=_read_intent(),
                prefer_over={"search_customers": PreferOverRule(when="x")},
            ),
        },
    )
    issues = validate_contract_against_snapshot(contract, _snapshot(get_customer, search_customers))
    assert len(issues) == 1
    assert "no behavioral contract entry" in issues[0].message


def test_validate_does_not_check_excludes_against_own_parameters() -> None:
    tool = _tool("get_customer")
    contract = BehavioralContract(
        schema_version="1",
        name="s",
        tools={
            "get_customer": ToolBehavior(intent=_read_intent(), excludes=["partial_name"]),
        },
    )
    issues = validate_contract_against_snapshot(contract, _snapshot(tool))
    assert issues == []
