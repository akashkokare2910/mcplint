from mcplint.config.schema import MCPLintConfig
from mcplint.models.findings import Severity


def test_defaults() -> None:
    config = MCPLintConfig()
    assert config.thresholds.ambiguity == 0.55
    assert config.severity == {}
    assert config.ignore == []
    assert config.benchmark is None


def test_severity_overrides_parse_as_enum() -> None:
    config = MCPLintConfig.model_validate({"severity": {"missing-tool-description": "error"}})
    assert config.severity["missing-tool-description"] == Severity.ERROR


def test_ignored_rule_ids_for_tool_specific_rules() -> None:
    config = MCPLintConfig.model_validate(
        {"ignore": [{"tool": "internal_debug", "rules": ["missing-return-semantics"]}]}
    )
    assert config.ignored_rule_ids_for_tool("internal_debug", {"a", "b"}) == {
        "missing-return-semantics"
    }
    assert config.ignored_rule_ids_for_tool("other_tool", {"a", "b"}) == set()


def test_ignored_rule_ids_for_tool_all_rules_when_empty_list() -> None:
    config = MCPLintConfig.model_validate({"ignore": [{"tool": "internal_debug", "rules": []}]})
    assert config.ignored_rule_ids_for_tool("internal_debug", {"a", "b"}) == {"a", "b"}
