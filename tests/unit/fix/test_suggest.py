from datetime import UTC, datetime

from mcplint.core.engine import lint_snapshot
from mcplint.core.registry import RuleRegistry
from mcplint.fix.suggest import build_suggestions, suggest_for_tool
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ParameterContract, SourceLocation, ToolAnnotation, ToolContract
from mcplint.models.findings import Finding, Severity
from mcplint.models.snapshot import MCPServerSnapshot


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


def test_suggest_for_tool_none_when_no_actionable_findings() -> None:
    tool = ToolContract(
        id="a",
        name="get_customer",
        description=(
            "Retrieve a single customer record by its exact customer identifier. "
            "Returns the customer's profile fields as JSON. Raises an error if "
            "the identifier does not exist."
        ),
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(read_only_hint=True, destructive_hint=False),
        raw={},
    )
    assert suggest_for_tool(tool, []) is None


def test_suggest_for_tool_documents_output_schema() -> None:
    # missing-return-semantics only fires when outputSchema is absent, so this
    # exercises suggest_for_tool's schema-description branch directly with a
    # hand-built finding rather than relying on the rule (which can't fire here).
    tool = ToolContract(
        id="a",
        name="get_customer",
        description="Retrieve a customer by ID.",
        input_schema={"type": "object", "properties": {}},
        output_schema={"type": "object", "properties": {"customer_id": {}, "name": {}}},
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    finding = Finding(
        rule_id="missing-return-semantics",
        severity=Severity.WARNING,
        message="synthetic",
        evidence="synthetic",
        location=SourceLocation(tool_name="get_customer", json_path="$.outputSchema"),
        remediation="synthetic",
        confidence=0.6,
    )
    suggestion = suggest_for_tool(tool, [finding])
    assert suggestion is not None
    assert "missing-return-semantics" in suggestion.resolved_rule_ids
    assert "customer_id" in suggestion.proposed_description
    assert "name" in suggestion.proposed_description


def test_suggest_for_tool_missing_return_semantics_without_schema() -> None:
    tool = ToolContract(
        id="a",
        name="fetch_record",
        description="Look up a record by its identifier in the internal store.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    report = lint_snapshot(_snapshot(tool), RuleRegistry.with_builtin_rules())
    suggestion = suggest_for_tool(tool, report.findings)
    assert suggestion is not None
    assert "missing-return-semantics" in suggestion.resolved_rule_ids
    assert "Document what this tool returns" in suggestion.proposed_description


def test_suggest_for_tool_states_enum_constraint() -> None:
    tool = ToolContract(
        id="a",
        name="search_customers",
        description="Search for customers matching a status.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[
            ParameterContract(
                name="status",
                json_schema={"type": "string", "enum": ["active", "inactive"]},
                required=True,
                description="The customer status.",
            )
        ],
        annotations=ToolAnnotation(),
        raw={},
    )
    report = lint_snapshot(_snapshot(tool), RuleRegistry.with_builtin_rules())
    suggestion = suggest_for_tool(tool, report.findings)
    assert suggestion is not None
    assert "undocumented-required-constraint" in suggestion.resolved_rule_ids
    assert "active" in suggestion.proposed_description
    assert "inactive" in suggestion.proposed_description


def test_suggest_for_tool_adds_destructive_warning() -> None:
    tool = ToolContract(
        id="a",
        name="delete_customer",
        description="Deletes a customer record.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(destructive_hint=True),
        raw={},
    )
    report = lint_snapshot(_snapshot(tool), RuleRegistry.with_builtin_rules())
    suggestion = suggest_for_tool(tool, report.findings)
    assert suggestion is not None
    assert "destructive-tool-without-warning" in suggestion.resolved_rule_ids
    assert "cannot be undone" in suggestion.proposed_description


def test_suggest_for_tool_truncates_long_description() -> None:
    long_description = "This is a sentence. " * 60
    tool = ToolContract(
        id="a",
        name="summarize_report",
        description=long_description,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    report = lint_snapshot(_snapshot(tool), RuleRegistry.with_builtin_rules())
    suggestion = suggest_for_tool(tool, report.findings)
    assert suggestion is not None
    assert "excessive-description-length" in suggestion.resolved_rule_ids
    assert len(suggestion.proposed_description) <= 800


def test_suggest_for_tool_vague_description_gets_low_confidence_placeholder() -> None:
    tool = ToolContract(
        id="a",
        name="do_thing",
        description="Does stuff.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    report = lint_snapshot(_snapshot(tool), RuleRegistry.with_builtin_rules())
    suggestion = suggest_for_tool(tool, report.findings)
    assert suggestion is not None
    assert "vague-tool-description" in suggestion.resolved_rule_ids
    assert suggestion.confidence <= 0.3
    assert "[TODO" in suggestion.proposed_description


def test_suggest_for_tool_adds_distinction_placeholder() -> None:
    shared_param = [
        ParameterContract(name="customer_id", json_schema={"type": "string"}, required=False)
    ]
    get_customer = ToolContract(
        id="a",
        name="get_customer",
        description="Retrieve a customer by ID.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=shared_param,
        annotations=ToolAnnotation(),
        raw={},
    )
    search_customer = ToolContract(
        id="b",
        name="search_customer",
        description="Retrieve a customer by search.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=shared_param,
        annotations=ToolAnnotation(),
        raw={},
    )
    report = lint_snapshot(
        _snapshot(get_customer, search_customer), RuleRegistry.with_builtin_rules()
    )
    own_findings = [f for f in report.findings if f.location.tool_name == "get_customer"]
    suggestion = suggest_for_tool(get_customer, own_findings)
    assert suggestion is not None
    assert "missing-tool-distinction" in suggestion.resolved_rule_ids
    assert "search_customer" in suggestion.proposed_description


def test_build_suggestions_skips_clean_tools() -> None:
    clean = ToolContract(
        id="a",
        name="get_customer",
        description=(
            "Retrieve a single customer record by its exact customer identifier. "
            "Returns the customer's profile fields as JSON. Raises an error if "
            "the identifier does not exist."
        ),
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(read_only_hint=True, destructive_hint=False),
        raw={},
    )
    dirty = ToolContract(
        id="b",
        name="do_thing",
        description="Does stuff.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    snapshot = _snapshot(clean, dirty)
    report = lint_snapshot(snapshot, RuleRegistry.with_builtin_rules())
    suggestions = build_suggestions(snapshot, report)
    tool_names = {s.tool_name for s in suggestions}
    assert "get_customer" not in tool_names
    assert "do_thing" in tool_names
