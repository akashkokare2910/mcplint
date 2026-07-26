"""Rules that judge a tool's top-level description text."""

from __future__ import annotations

import re

from mcplint.core.rules.base import Rule, RuleContext
from mcplint.models.contracts import SourceLocation, ToolContract
from mcplint.models.findings import Finding, Severity

MIN_DESCRIPTION_WORDS = 4


def _normalize_words(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return [word for word in cleaned.split() if word]


class MissingToolDescriptionRule(Rule):
    id = "missing-tool-description"
    title = "Missing tool description"
    description = "Flags tools with no description or a whitespace-only description."
    default_severity = Severity.ERROR
    tags = ("description",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        if tool.description is not None and tool.description.strip():
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.default_severity,
                message=f"Tool '{tool.name}' has no description.",
                evidence="description is missing or blank",
                location=SourceLocation(tool_name=tool.name, json_path="$.description"),
                remediation=(
                    "Add a description explaining what the tool does, its inputs, "
                    "and when an agent should choose it over similar tools."
                ),
                confidence=1.0,
            )
        ]


class DescriptionRepeatsNameRule(Rule):
    id = "description-repeats-name"
    title = "Description repeats the tool name"
    description = (
        "Flags descriptions that only restate the tool name in words, adding no "
        "information beyond what the name already conveys."
    )
    default_severity = Severity.WARNING
    tags = ("description",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        if not tool.description or not tool.description.strip():
            return []
        name_words = _normalize_words(tool.name.replace("_", " ").replace("-", " "))
        description_words = _normalize_words(tool.description)
        if description_words != name_words:
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.default_severity,
                message=f"Tool '{tool.name}' description only restates its name.",
                evidence=(
                    f"description '{tool.description}' normalizes to the same words "
                    "as the tool name"
                ),
                location=SourceLocation(tool_name=tool.name, json_path="$.description"),
                remediation=(
                    "Explain what the tool actually does: inputs, output shape, "
                    "side effects, and when to prefer it over similar tools."
                ),
                confidence=0.9,
            )
        ]


class VagueToolDescriptionRule(Rule):
    id = "vague-tool-description"
    title = "Vague tool description"
    description = (
        f"Flags descriptions shorter than {MIN_DESCRIPTION_WORDS} words as likely too "
        "vague to disambiguate tool choice."
    )
    default_severity = Severity.WARNING
    tags = ("description",)

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        if not tool.description or not tool.description.strip():
            return []
        words = _normalize_words(tool.description)
        if len(words) >= MIN_DESCRIPTION_WORDS:
            return []
        return [
            Finding(
                rule_id=self.id,
                severity=self.default_severity,
                message=f"Tool '{tool.name}' description is very short ({len(words)} words).",
                evidence=f"description: '{tool.description}'",
                location=SourceLocation(tool_name=tool.name, json_path="$.description"),
                remediation=(
                    "Expand the description with the specific action, inputs, and "
                    "when an agent should use this tool versus alternatives."
                ),
                confidence=0.7,
            )
        ]
