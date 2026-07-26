"""Rules that check a tool's name and annotations agree about how dangerous it is."""

from __future__ import annotations

import re

from mcplint.core.rules.base import Rule, RuleContext
from mcplint.models.contracts import SourceLocation, ToolContract
from mcplint.models.findings import Finding, Severity

READ_VERBS = frozenset({"get", "list", "search", "find", "fetch", "query", "view", "show", "read"})
WRITE_VERBS = frozenset(
    {
        "create",
        "update",
        "delete",
        "remove",
        "set",
        "add",
        "modify",
        "edit",
        "insert",
        "upsert",
        "patch",
    }
)
_DESTRUCTIVE_WARNING_HINTS = re.compile(
    r"\b(permanent|permanently|irreversible|cannot be undone|cannot be reversed|destructive)\b",
    re.IGNORECASE,
)


def first_word(name: str) -> str:
    return re.split(r"[_\-]", name, maxsplit=1)[0].lower()


class ToolNameActionConflictRule(Rule):
    id = "tool-name-action-conflict"
    title = "Tool name conflicts with its destructive annotation"
    description = (
        "Flags tools whose name reads as a read-only action (get/list/search/...) "
        "but which are annotated as destructive."
    )
    default_severity = Severity.ERROR
    tags = ("safety",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        if first_word(tool.name) not in READ_VERBS:
            return []
        if not tool.annotations.destructive_hint:
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.default_severity,
                message=(
                    f"Tool '{tool.name}' reads as a read-only action but is annotated destructive."
                ),
                evidence=(
                    f"name starts with a read verb ('{first_word(tool.name)}') "
                    "but annotations.destructiveHint is true"
                ),
                location=SourceLocation(
                    tool_name=tool.name, json_path="$.annotations.destructiveHint"
                ),
                remediation=(
                    "Rename the tool to reflect its real effect, or correct the "
                    "destructive annotation if the tool is genuinely read-only."
                ),
                confidence=0.7,
            )
        ]


class DestructiveToolWithoutWarningRule(Rule):
    id = "destructive-tool-without-warning"
    title = "Destructive tool without a warning"
    description = (
        "Flags tools annotated destructive whose description does not warn that "
        "the action is permanent or irreversible."
    )
    default_severity = Severity.ERROR
    tags = ("safety",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        if not tool.annotations.destructive_hint:
            return []
        if tool.description and _DESTRUCTIVE_WARNING_HINTS.search(tool.description):
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.default_severity,
                message=f"Tool '{tool.name}' is destructive but its description has no warning.",
                evidence="annotations.destructiveHint is true, no warning wording in description",
                location=SourceLocation(tool_name=tool.name, json_path="$.description"),
                remediation=(
                    "State plainly that the action is permanent/irreversible and "
                    "cannot be undone, so an agent hesitates before calling it."
                ),
                confidence=0.8,
            )
        ]


class StateChangingToolMarkedReadOnlyRule(Rule):
    id = "state-changing-tool-marked-read-only"
    title = "State-changing tool marked read-only"
    description = (
        "Flags tools whose name reads as a mutation (create/update/delete/...) "
        "but which are annotated readOnlyHint=true."
    )
    default_severity = Severity.ERROR
    tags = ("safety",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        if first_word(tool.name) not in WRITE_VERBS:
            return []
        if tool.annotations.read_only_hint is not True:
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.default_severity,
                message=f"Tool '{tool.name}' changes state but is annotated read-only.",
                evidence=(
                    f"name starts with a write verb ('{first_word(tool.name)}') "
                    "but annotations.readOnlyHint is true"
                ),
                location=SourceLocation(
                    tool_name=tool.name, json_path="$.annotations.readOnlyHint"
                ),
                remediation=(
                    "Correct readOnlyHint to false for this tool, since agents may "
                    "rely on it to decide whether a call is safe to retry or sandbox."
                ),
                confidence=0.8,
            )
        ]
