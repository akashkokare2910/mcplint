"""Rules that cross-check a tool's parameter descriptions against its JSON Schema."""

from __future__ import annotations

import re

from mcplint.core.rules.base import Rule, RuleContext
from mcplint.models.contracts import SourceLocation, ToolContract
from mcplint.models.findings import Finding, Severity

_NUMERIC_HINTS = re.compile(r"\b(number of|count of|quantity of|amount of)\b", re.IGNORECASE)
_LIST_HINTS = re.compile(r"\b(list of|array of|comma-separated list of)\b", re.IGNORECASE)
_BOOLEAN_HINTS = re.compile(r"\b(true or false|boolean flag|yes or no)\b", re.IGNORECASE)


class MissingParameterDescriptionRule(Rule):
    id = "missing-parameter-description"
    title = "Missing parameter description"
    description = "Flags input parameters with no description."
    default_severity = Severity.WARNING
    tags = ("schema",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        findings = []
        for param in tool.parameters:
            if param.description and param.description.strip():
                continue
            findings.append(
                Finding(
                    rule_id=self.id,
                    severity=self.default_severity,
                    message=f"Parameter '{param.name}' on tool '{tool.name}' has no description.",
                    evidence="parameter description is missing or blank",
                    location=SourceLocation(
                        tool_name=tool.name, json_path=f"$.inputSchema.properties.{param.name}"
                    ),
                    remediation=(
                        f"Document '{param.name}': its purpose, expected format, and any "
                        "constraints not already captured by the schema."
                    ),
                    confidence=1.0,
                )
            )
        return findings


class SchemaDescriptionTypeConflictRule(Rule):
    id = "schema-description-type-conflict"
    title = "Description conflicts with parameter schema type"
    description = (
        "Flags parameters whose description implies a different JSON Schema type "
        "than the one declared (e.g. 'number of X' on a string-typed parameter)."
    )
    default_severity = Severity.ERROR
    tags = ("schema",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        findings = []
        for param in tool.parameters:
            if not param.description or not param.description.strip():
                continue
            declared_type = param.json_schema.get("type")
            conflict = self._detect_conflict(param.description, declared_type)
            if conflict is None:
                continue
            expected_type, hint = conflict
            findings.append(
                Finding(
                    rule_id=self.id,
                    severity=self.default_severity,
                    message=(
                        f"Parameter '{param.name}' on tool '{tool.name}' reads as "
                        f"{expected_type!r} but the schema declares type {declared_type!r}."
                    ),
                    evidence=(
                        f"description matched pattern '{hint}', schema type is {declared_type!r}"
                    ),
                    location=SourceLocation(
                        tool_name=tool.name, json_path=f"$.inputSchema.properties.{param.name}.type"
                    ),
                    remediation=(
                        f"Either change the schema type to {expected_type!r} or rewrite the "
                        "description so it matches the declared type."
                    ),
                    confidence=0.6,
                )
            )
        return findings

    @staticmethod
    def _detect_conflict(description: str, declared_type: object) -> tuple[str, str] | None:
        numeric_match = _NUMERIC_HINTS.search(description)
        if numeric_match and declared_type not in ("integer", "number"):
            return "integer", numeric_match.group(0)
        list_match = _LIST_HINTS.search(description)
        if list_match and declared_type != "array":
            return "array", list_match.group(0)
        boolean_match = _BOOLEAN_HINTS.search(description)
        if boolean_match and declared_type != "boolean":
            return "boolean", boolean_match.group(0)
        return None
