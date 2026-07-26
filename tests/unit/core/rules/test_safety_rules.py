from datetime import UTC, datetime

from mcplint.core.rules.base import RuleContext
from mcplint.core.rules.safety_rules import (
    DestructiveToolWithoutWarningRule,
    StateChangingToolMarkedReadOnlyRule,
    ToolNameActionConflictRule,
)
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot


def _tool(name: str, description: str | None, annotations: ToolAnnotation) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description=description,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=annotations,
        raw={},
    )


def _context(tool: ToolContract) -> RuleContext:
    snapshot = MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0", generated_at=datetime(2026, 1, 1, tzinfo=UTC), mcplint_version="0.1.0"
        ),
        server_name="s",
        server_version=None,
        transport="stdio",
        command=None,
        tools=[tool],
    )
    return RuleContext(snapshot=snapshot)


def test_tool_name_action_conflict_flags_read_verb_with_destructive_hint() -> None:
    tool = _tool("get_customer", "Fetch a customer.", ToolAnnotation(destructive_hint=True))
    findings = ToolNameActionConflictRule().check(tool, _context(tool))
    assert len(findings) == 1


def test_tool_name_action_conflict_passes_when_consistent() -> None:
    tool = _tool("get_customer", "Fetch a customer.", ToolAnnotation(destructive_hint=False))
    assert ToolNameActionConflictRule().check(tool, _context(tool)) == []


def test_destructive_tool_without_warning_flags_missing_warning() -> None:
    tool = _tool(
        "delete_customer", "Deletes a customer record.", ToolAnnotation(destructive_hint=True)
    )
    findings = DestructiveToolWithoutWarningRule().check(tool, _context(tool))
    assert len(findings) == 1


def test_destructive_tool_without_warning_passes_with_warning() -> None:
    tool = _tool(
        "delete_customer",
        "Permanently deletes a customer record. This cannot be undone.",
        ToolAnnotation(destructive_hint=True),
    )
    assert DestructiveToolWithoutWarningRule().check(tool, _context(tool)) == []


def test_destructive_tool_without_warning_skips_non_destructive() -> None:
    tool = _tool("get_customer", "Fetch a customer.", ToolAnnotation(destructive_hint=False))
    assert DestructiveToolWithoutWarningRule().check(tool, _context(tool)) == []


def test_state_changing_tool_marked_read_only_flags_conflict() -> None:
    tool = _tool(
        "update_customer", "Updates a customer record.", ToolAnnotation(read_only_hint=True)
    )
    findings = StateChangingToolMarkedReadOnlyRule().check(tool, _context(tool))
    assert len(findings) == 1


def test_state_changing_tool_marked_read_only_passes_when_correct() -> None:
    tool = _tool(
        "update_customer", "Updates a customer record.", ToolAnnotation(read_only_hint=False)
    )
    assert StateChangingToolMarkedReadOnlyRule().check(tool, _context(tool)) == []
