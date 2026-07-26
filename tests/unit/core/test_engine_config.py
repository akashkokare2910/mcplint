from datetime import UTC, datetime

from mcplint.config.schema import IgnoreEntry, MCPLintConfig
from mcplint.core.engine import lint_snapshot
from mcplint.core.registry import RuleRegistry
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.findings import Severity
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


def _undocumented_tool(name: str = "internal_debug") -> ToolContract:
    return ToolContract(
        id="a",
        name=name,
        description=None,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )


def test_lint_snapshot_respects_ignore_config() -> None:
    tool = _undocumented_tool("internal_debug")
    config = MCPLintConfig(
        ignore=[IgnoreEntry(tool="internal_debug", rules=["missing-tool-description"])]
    )
    report = lint_snapshot(_snapshot(tool), RuleRegistry.with_builtin_rules(config), config)
    assert "missing-tool-description" not in {f.rule_id for f in report.findings}


def test_lint_snapshot_ignore_all_rules_for_tool() -> None:
    tool = _undocumented_tool("internal_debug")
    config = MCPLintConfig(ignore=[IgnoreEntry(tool="internal_debug", rules=[])])
    report = lint_snapshot(_snapshot(tool), RuleRegistry.with_builtin_rules(config), config)
    assert report.findings == []


def test_lint_snapshot_applies_severity_override() -> None:
    tool = _undocumented_tool("delete_customer")
    config = MCPLintConfig(severity={"missing-tool-description": Severity.INFO})
    report = lint_snapshot(_snapshot(tool), RuleRegistry.with_builtin_rules(config), config)
    finding = next(f for f in report.findings if f.rule_id == "missing-tool-description")
    assert finding.severity == Severity.INFO


def test_with_builtin_rules_applies_ambiguity_threshold() -> None:
    config = MCPLintConfig(thresholds={"ambiguity": 0.9, "max_description_characters": 800})
    registry = RuleRegistry.with_builtin_rules(config)
    rule = registry.get("ambiguous-tool-overlap")
    assert rule is not None
    assert rule.threshold == 0.9  # type: ignore[attr-defined]
