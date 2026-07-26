from datetime import UTC, datetime

import pytest

from mcplint.core.registry import RuleRegistry
from mcplint.core.rules.base import Rule, RuleContext
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolContract
from mcplint.models.findings import Finding, Severity
from mcplint.models.snapshot import MCPServerSnapshot


class _FakeRule(Rule):
    id = "fake-rule"
    title = "Fake rule"
    description = "A rule used only in tests."
    default_severity = Severity.INFO

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        return []


def test_register_and_get() -> None:
    registry = RuleRegistry()
    registry.register(_FakeRule())
    found = registry.get("fake-rule")
    assert found is not None
    assert found.metadata().title == "Fake rule"


def test_register_duplicate_raises() -> None:
    registry = RuleRegistry()
    registry.register(_FakeRule())
    with pytest.raises(ValueError, match="fake-rule"):
        registry.register(_FakeRule())


def test_all_sorted_by_id() -> None:
    class _ARule(_FakeRule):
        id = "a-rule"

    class _ZRule(_FakeRule):
        id = "z-rule"

    registry = RuleRegistry()
    registry.register(_ZRule())
    registry.register(_ARule())
    assert [rule.id for rule in registry.all()] == ["a-rule", "z-rule"]


def test_rule_context_holds_snapshot() -> None:
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
        tools=[],
    )
    context = RuleContext(snapshot=snapshot)
    assert context.snapshot.server_name == "s"


def test_with_builtin_rules_registers_all_fifteen() -> None:
    registry = RuleRegistry.with_builtin_rules()
    ids = {rule.id for rule in registry.all()}
    assert ids == {
        "missing-tool-description",
        "description-repeats-name",
        "vague-tool-description",
        "missing-parameter-description",
        "missing-return-semantics",
        "undocumented-error-behaviour",
        "undocumented-required-constraint",
        "schema-description-type-conflict",
        "tool-name-action-conflict",
        "destructive-tool-without-warning",
        "state-changing-tool-marked-read-only",
        "ambiguous-tool-overlap",
        "missing-tool-distinction",
        "excessive-description-length",
        "undefined-domain-term",
    }
    assert len(ids) == 15
