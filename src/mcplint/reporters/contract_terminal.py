"""Render contract-validation issues as Rich terminal text."""

from __future__ import annotations

from io import StringIO

from rich.console import Console
from rich.table import Table

from mcplint.contract.validator import ContractValidationIssue


def render_contract_validation_terminal(
    contract_name: str, issues: list[ContractValidationIssue]
) -> str:
    buffer = StringIO()
    console = Console(file=buffer, width=140, record=True)

    if not issues:
        console.print(f"[green]'{contract_name}' is consistent with the snapshot.[/green]")
        return buffer.getvalue()

    console.print(f"[bold red]{len(issues)} issue(s) in '{contract_name}':[/bold red]")
    table = Table()
    table.add_column("Tool")
    table.add_column("Issue")
    for issue in issues:
        table.add_row(issue.tool_name, issue.message)
    console.print(table)

    return buffer.getvalue()
