"""Collects built-in and plugin rules for the lint engine to run."""

from __future__ import annotations

from importlib.metadata import entry_points

from mcplint.core.rules.base import Rule


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
    def with_builtin_rules(cls) -> RuleRegistry:
        from mcplint.core.rules.builtin import BUILTIN_RULES

        registry = cls()
        for rule_cls in BUILTIN_RULES:
            registry.register(rule_cls())
        return registry
