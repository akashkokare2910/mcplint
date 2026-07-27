"""`mcplint rules`: list every built-in rule."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from mcplint.core.registry import RuleRegistry

console = Console(width=160)


def rules_command() -> None:
    registry = RuleRegistry.with_builtin_rules()
    table = Table(title="MCPLint rule catalogue")
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Default severity")
    table.add_column("Tags")

    for rule in registry.all():
        metadata = rule.metadata()
        table.add_row(
            metadata.id,
            metadata.title,
            metadata.default_severity.value,
            ", ".join(metadata.tags),
        )

    console.print(table)
