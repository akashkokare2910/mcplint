"""Cross-checks a BehavioralContract against a real MCPServerSnapshot.

A contract can be syntactically valid YAML but describe a server that no
longer exists in this shape: a renamed tool, a `prefer_over` target that
was removed, a `requires` parameter that was renamed. This catches that
drift before it silently breaks adversarial generation or mutation testing.
"""

from __future__ import annotations

from pydantic import BaseModel

from mcplint.models.contract import BehavioralContract
from mcplint.models.snapshot import MCPServerSnapshot


class ContractValidationIssue(BaseModel):
    tool_name: str
    message: str


def validate_contract_against_snapshot(
    contract: BehavioralContract, snapshot: MCPServerSnapshot
) -> list[ContractValidationIssue]:
    issues: list[ContractValidationIssue] = []
    snapshot_tool_names = {tool.name for tool in snapshot.tools}

    for tool_name, behavior in contract.tools.items():
        if tool_name not in snapshot_tool_names:
            issues.append(
                ContractValidationIssue(
                    tool_name=tool_name,
                    message=f"Contract describes tool '{tool_name}', which does not exist "
                    "in the snapshot.",
                )
            )
            continue

        tool = snapshot.get_tool(tool_name)
        assert tool is not None
        param_names = tool.parameter_names()

        for required_param in behavior.requires:
            if required_param not in param_names:
                issues.append(
                    ContractValidationIssue(
                        tool_name=tool_name,
                        message=f"'requires' references parameter '{required_param}', which "
                        f"is not a parameter of '{tool_name}'.",
                    )
                )

        for other_tool_name in behavior.prefer_over:
            if other_tool_name not in snapshot_tool_names:
                issues.append(
                    ContractValidationIssue(
                        tool_name=tool_name,
                        message=f"'prefer_over' references tool '{other_tool_name}', which "
                        "does not exist in the snapshot.",
                    )
                )
            elif other_tool_name not in contract.tools:
                issues.append(
                    ContractValidationIssue(
                        tool_name=tool_name,
                        message=f"'prefer_over' references tool '{other_tool_name}', which "
                        "exists in the snapshot but has no behavioral contract entry.",
                    )
                )

    return issues
