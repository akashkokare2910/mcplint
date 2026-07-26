from datetime import UTC, datetime

from mcplint.core.engine import lint_snapshot
from mcplint.core.registry import RuleRegistry
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _snapshot(*tools: ToolContract) -> MCPServerSnapshot:
    return MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="customer-server",
        server_version=None,
        transport="stdio",
        command=None,
        tools=list(tools),
    )


def test_lint_snapshot_collects_findings_across_tools() -> None:
    undocumented = ToolContract(
        id="a",
        name="delete_customer",
        description=None,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    documented = ToolContract(
        id="b",
        name="get_customer",
        description="Retrieve a single customer record by its exact customer ID.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    report = lint_snapshot(_snapshot(undocumented, documented), RuleRegistry.with_builtin_rules())
    assert report.server_name == "customer-server"
    rule_ids = {f.rule_id for f in report.findings}
    assert "missing-tool-description" in rule_ids
    assert all(
        f.location.tool_name == "delete_customer"
        for f in report.findings
        if f.rule_id == "missing-tool-description"
    )


def test_lint_snapshot_clean_server_has_no_findings() -> None:
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
    report = lint_snapshot(_snapshot(clean), RuleRegistry.with_builtin_rules())
    assert report.findings == []
