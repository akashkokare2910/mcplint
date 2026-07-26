"""Collects built-in and plugin rules for the lint engine to run."""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import TYPE_CHECKING

from mcplint.core.rules.base import Rule

if TYPE_CHECKING:
    from mcplint.config.schema import MCPLintConfig


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(self, rule: Rule) -> None:
        if rule.id in self._rules:
            raise ValueError(f"Rule '{rule.id}' is already registered")
        self._rules[rule.id] = rule

    def get(self, rule_id: str) -> Rule | None:
        return self._rules.get(rule_id)

    def all(self) -> list[Rule]:
        return [self._rules[key] for key in sorted(self._rules)]

    def load_entry_point_plugins(self) -> None:
        for entry_point in entry_points(group="mcplint.rules"):
            rule_cls = entry_point.load()
            self.register(rule_cls())

    @classmethod
    def with_builtin_rules(cls, config: MCPLintConfig | None = None) -> RuleRegistry:
        from mcplint.core.rules.ambiguity_rules import (
            AmbiguousToolOverlapRule,
            MissingToolDistinctionRule,
        )
        from mcplint.core.rules.builtin import BUILTIN_RULES
        from mcplint.core.rules.completeness_rules import ExcessiveDescriptionLengthRule

        registry = cls()
        for rule_cls in BUILTIN_RULES:
            rule = rule_cls()
            if config is not None:
                if isinstance(rule, AmbiguousToolOverlapRule | MissingToolDistinctionRule):
                    rule.threshold = config.thresholds.ambiguity
                elif isinstance(rule, ExcessiveDescriptionLengthRule):
                    rule.max_characters = config.thresholds.max_description_characters
            registry.register(rule)
        return registry
