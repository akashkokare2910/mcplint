"""Rules that flag gaps in what a tool's description documents.

`excessive-description-length`'s threshold is a module default; Phase 3's
configuration loader overrides it via `mcplint.yaml` (`thresholds.max_description_characters`).
"""

from __future__ import annotations

import re

from mcplint.core.rules.base import Rule, RuleContext
from mcplint.models.contracts import SourceLocation, ToolContract
from mcplint.models.findings import Finding, Severity

DEFAULT_MAX_DESCRIPTION_CHARACTERS = 800

_RETURN_HINTS = re.compile(r"\b(returns?|returning|output|result|response)\b", re.IGNORECASE)
_ERROR_HINTS = re.compile(
    r"\b(error|fail|failure|exception|raise|raises|throws|invalid|not found)\b", re.IGNORECASE
)
_CONSTRAINT_KEYS = ("minimum", "maximum", "minLength", "maxLength", "pattern", "enum")
_WELL_KNOWN_ACRONYMS = {
    "ID",
    "URL",
    "URI",
    "API",
    "JSON",
    "XML",
    "HTTP",
    "HTTPS",
    "UUID",
    "SQL",
    "CSV",
    "PDF",
    "UTC",
    "OK",
}
_ACRONYM_PATTERN = re.compile(r"\b[A-Z]{2,6}\b")


class MissingReturnSemanticsRule(Rule):
    id = "missing-return-semantics"
    title = "Missing return semantics"
    description = (
        "Flags tools with no outputSchema whose description also never explains "
        "what the tool returns."
    )
    default_severity = Severity.WARNING
    tags = ("completeness",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        if tool.output_schema is not None:
            return []
        if tool.description and _RETURN_HINTS.search(tool.description):
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.default_severity,
                message=f"Tool '{tool.name}' does not document what it returns.",
                evidence="no outputSchema and no return-related wording in the description",
                location=SourceLocation(tool_name=tool.name, json_path="$.outputSchema"),
                remediation=(
                    "Add an outputSchema, or describe the shape and meaning of the "
                    "tool's return value in its description."
                ),
                confidence=0.6,
            )
        ]


class UndocumentedErrorBehaviourRule(Rule):
    id = "undocumented-error-behaviour"
    title = "Undocumented error behaviour"
    description = "Flags tools whose description never mentions failure or error conditions."
    default_severity = Severity.INFO
    tags = ("completeness",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        if not tool.description or not tool.description.strip():
            return []
        if _ERROR_HINTS.search(tool.description):
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.default_severity,
                message=f"Tool '{tool.name}' does not document its error behaviour.",
                evidence="no error/failure/exception wording found in the description",
                location=SourceLocation(tool_name=tool.name, json_path="$.description"),
                remediation=(
                    "Document how the tool signals failure: what happens on an "
                    "invalid input, a not-found lookup, or an internal error."
                ),
                confidence=0.5,
            )
        ]


class UndocumentedRequiredConstraintRule(Rule):
    id = "undocumented-required-constraint"
    title = "Undocumented required-parameter constraint"
    description = (
        "Flags required parameters whose JSON Schema constraints (enum, min/max, "
        "pattern, length) are not mentioned in the parameter description."
    )
    default_severity = Severity.WARNING
    tags = ("completeness", "schema")

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        findings = []
        for param in tool.parameters:
            if not param.required or not param.description:
                continue
            description_lower = param.description.lower()
            for key in _CONSTRAINT_KEYS:
                if key not in param.json_schema:
                    continue
                value = param.json_schema[key]
                if self._is_documented(value, description_lower):
                    continue
                findings.append(
                    Finding(
                        rule_id=self.id,
                        severity=self.default_severity,
                        message=(
                            f"Parameter '{param.name}' on tool '{tool.name}' has a "
                            f"'{key}' constraint not reflected in its description."
                        ),
                        evidence=f"schema {key}={value!r}, not mentioned in description",
                        location=SourceLocation(
                            tool_name=tool.name,
                            json_path=f"$.inputSchema.properties.{param.name}.{key}",
                        ),
                        remediation=(
                            f"Mention the '{key}' constraint ({value!r}) in the "
                            f"description of '{param.name}'."
                        ),
                        confidence=0.6,
                    )
                )
        return findings

    @staticmethod
    def _is_documented(value: object, description_lower: str) -> bool:
        if isinstance(value, list):
            return any(str(item).lower() in description_lower for item in value)
        return str(value).lower() in description_lower


class ExcessiveDescriptionLengthRule(Rule):
    id = "excessive-description-length"
    title = "Excessive description length"
    description = (
        f"Flags descriptions longer than {DEFAULT_MAX_DESCRIPTION_CHARACTERS} characters, "
        "which risk burning context and burying the useful details."
    )
    default_severity = Severity.INFO
    tags = ("description",)
    max_characters = DEFAULT_MAX_DESCRIPTION_CHARACTERS

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        if not tool.description or len(tool.description) <= self.max_characters:
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.default_severity,
                message=(
                    f"Tool '{tool.name}' description is {len(tool.description)} characters, "
                    f"over the {self.max_characters}-character guideline."
                ),
                evidence=f"description length: {len(tool.description)}",
                location=SourceLocation(tool_name=tool.name, json_path="$.description"),
                remediation=(
                    "Trim the description to the essential behaviour, inputs, and distinctions."
                ),
                confidence=0.8,
            )
        ]


class UndefinedDomainTermRule(Rule):
    id = "undefined-domain-term"
    title = "Undefined domain term"
    description = (
        "Flags acronyms or domain-specific terms used in a description without "
        "being defined nearby, which an agent outside the domain may misread."
    )
    default_severity = Severity.INFO
    tags = ("description",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        if not tool.description:
            return []
        findings = []
        seen: set[str] = set()
        for match in _ACRONYM_PATTERN.finditer(tool.description):
            term = match.group(0)
            if term in _WELL_KNOWN_ACRONYMS or term in seen:
                continue
            following = tool.description[match.end() : match.end() + 2]
            if following.startswith(" (") or following.startswith("("):
                continue
            seen.add(term)
            findings.append(
                Finding(
                    rule_id=self.id,
                    severity=self.default_severity,
                    message=f"Tool '{tool.name}' description uses undefined term '{term}'.",
                    evidence=f"'{term}' appears without a nearby definition",
                    location=SourceLocation(tool_name=tool.name, json_path="$.description"),
                    remediation=f"Define '{term}' on first use, e.g. '{term} (...)'.",
                    confidence=0.4,
                )
            )
        return findings
