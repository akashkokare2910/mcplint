from datetime import UTC, datetime

from mcplint.core.rules.ambiguity_rules import AmbiguousToolOverlapRule, MissingToolDistinctionRule
from mcplint.core.rules.base import RuleContext
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ParameterContract, ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _tool(name: str, description: str | None) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description=description,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[
            ParameterContract(name="customer_id", json_schema={"type": "string"}, required=False)
        ],
        annotations=ToolAnnotation(read_only_hint=True),
        raw={},
    )


def _context(*tools: ToolContract) -> RuleContext:
    snapshot = MCPServerSnapshot(
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
    return RuleContext(snapshot=snapshot)


def test_ambiguous_tool_overlap_flags_pair_once() -> None:
    get_customer = _tool("get_customer", "Retrieve a customer record by its ID.")
    search_customer = _tool("search_customer", "Retrieve a customer record by search criteria.")
    context = _context(get_customer, search_customer)

    rule = AmbiguousToolOverlapRule()
    findings_from_get = rule.check(get_customer, context)
    findings_from_search = rule.check(search_customer, context)

    assert len(findings_from_get) == 1
    assert findings_from_search == []


def test_ambiguous_tool_overlap_passes_for_unrelated_tools() -> None:
    get_customer = _tool("get_customer", "Retrieve a customer record by its ID.")
    send_email = _tool("send_email", "Send an email notification to a mailing list.")
    context = _context(get_customer, send_email)
    assert AmbiguousToolOverlapRule().check(get_customer, context) == []


def test_missing_tool_distinction_flags_absent_exact_vs_search() -> None:
    get_customer = _tool("get_customer", "Retrieve a customer by ID.")
    search_customer = _tool("search_customer", "Retrieve a customer by search.")
    context = _context(get_customer, search_customer)
    findings = MissingToolDistinctionRule().check(get_customer, context)
    assert len(findings) == 1
    assert "exact-vs-search" in findings[0].evidence


def test_missing_tool_distinction_passes_when_distinction_present() -> None:
    get_customer = _tool(
        "get_customer",
        "Retrieve a single customer by its exact ID. Use search_customer for multiple results.",
    )
    search_customer = _tool(
        "search_customer",
        "Retrieve a list of customers by search when you don't have the exact ID.",
    )
    context = _context(get_customer, search_customer)
    assert MissingToolDistinctionRule().check(get_customer, context) == []
