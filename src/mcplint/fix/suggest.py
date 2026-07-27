"""Deterministic rewrite suggestions built directly from JSON Schema and
annotations: no LLM. Each fixable finding contributes one clause appended
to the tool's existing description (or, for excessive-description-length,
a deterministic truncation). Purely semantic issues (vague wording, a
description that just restates the name, or a missing description) cannot
be fixed with fabricated prose in deterministic mode: they get a low-
confidence TODO placeholder instead, honestly flagged as needing manual or
LLM-assisted rewriting.
"""

from __future__ import annotations

import re

from mcplint.models.contracts import ToolContract
from mcplint.models.findings import Finding, LintReport
from mcplint.models.fixes import RewriteSuggestion
from mcplint.models.snapshot import MCPServerSnapshot

_SEMANTIC_PLACEHOLDER_RULES = frozenset(
    {"missing-tool-description", "description-repeats-name", "vague-tool-description"}
)
_ACTIONABLE_RULE_IDS = _SEMANTIC_PLACEHOLDER_RULES | frozenset(
    {
        "missing-return-semantics",
        "undocumented-required-constraint",
        "destructive-tool-without-warning",
        "missing-tool-distinction",
        "excessive-description-length",
    }
)

_OTHER_TOOL_PATTERN = re.compile(r"'([a-zA-Z0-9_-]+)'")


def _describe_output_schema(schema: dict[str, object]) -> str:
    properties = schema.get("properties")
    if isinstance(properties, dict) and properties:
        fields = ", ".join(sorted(properties))
        return f"Returns an object with fields: {fields}."
    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        return f"Returns a value of type '{schema_type}'."
    return "Returns a result."


def _constraint_clause(param_name: str, schema: dict[str, object]) -> str | None:
    enum_values = schema.get("enum")
    if isinstance(enum_values, list):
        values = ", ".join(str(v) for v in enum_values)
        return f"Parameter '{param_name}' accepts: {values}."
    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    if minimum is not None and maximum is not None:
        return f"Parameter '{param_name}' must be between {minimum} and {maximum}."
    if minimum is not None:
        return f"Parameter '{param_name}' must be at least {minimum}."
    if maximum is not None:
        return f"Parameter '{param_name}' must be at most {maximum}."
    return None


def _other_tool_name(message: str, this_tool: str) -> str | None:
    names = [name for name in _OTHER_TOOL_PATTERN.findall(message) if name != this_tool]
    return names[0] if names else None


def _truncate_description(description: str, max_characters: int) -> str:
    if len(description) <= max_characters:
        return description
    truncated = description[:max_characters]
    last_period = truncated.rfind(". ")
    if last_period > 0:
        return truncated[: last_period + 1]
    return truncated.rstrip() + "…"


def suggest_for_tool(tool: ToolContract, findings: list[Finding]) -> RewriteSuggestion | None:
    actionable = [f for f in findings if f.rule_id in _ACTIONABLE_RULE_IDS]
    if not actionable:
        return None

    base = (tool.description or "").strip()
    clauses: list[str] = []
    resolved_rule_ids: list[str] = []
    explanations: list[str] = []
    confidences: list[float] = []

    for finding in actionable:
        rule_id = finding.rule_id

        if rule_id == "missing-return-semantics":
            if tool.output_schema:
                clauses.append(_describe_output_schema(tool.output_schema))
                explanations.append("Documented the return shape from outputSchema.")
                confidences.append(0.9)
            else:
                clauses.append("Document what this tool returns (e.g. field names and types).")
                explanations.append("Flagged the missing return description for manual detail.")
                confidences.append(0.4)
            resolved_rule_ids.append(rule_id)

        elif rule_id == "undocumented-required-constraint":
            parts = finding.location.json_path.split(".")
            param_name = parts[3] if len(parts) > 3 else None
            param = next((p for p in tool.parameters if p.name == param_name), None)
            clause = _constraint_clause(param.name, param.json_schema) if param else None
            if clause:
                clauses.append(clause)
                resolved_rule_ids.append(rule_id)
                explanations.append(f"Stated the '{param_name}' constraint from its JSON Schema.")
                confidences.append(0.85)

        elif rule_id == "destructive-tool-without-warning":
            clauses.append("This action is permanent and cannot be undone.")
            resolved_rule_ids.append(rule_id)
            explanations.append("Added a destructive-operation warning.")
            confidences.append(0.9)

        elif rule_id == "missing-tool-distinction":
            other = _other_tool_name(finding.message, tool.name)
            if other:
                clauses.append(
                    f"See {other} for a related but different operation: check both "
                    "descriptions before choosing."
                )
                resolved_rule_ids.append(rule_id)
                explanations.append(
                    f"Added a placeholder distinction between '{tool.name}' and '{other}'; "
                    "refine the wording manually or with LLM-assisted rewriting."
                )
                confidences.append(0.35)

        elif rule_id in _SEMANTIC_PLACEHOLDER_RULES:
            placeholder = (
                "[TODO: describe the specific action, inputs, and output of this tool, "
                "and when to use it instead of similar tools]"
            )
            if placeholder not in clauses:
                clauses.append(placeholder)
                resolved_rule_ids.append(rule_id)
                explanations.append(
                    "Flagged for manual or LLM-assisted rewriting: deterministic mode "
                    "cannot fabricate semantic content."
                )
                confidences.append(0.2)

    # Truncation takes precedence over appended clauses: adding more text would
    # defeat the point of shortening an over-long description.
    length_finding = next(
        (f for f in actionable if f.rule_id == "excessive-description-length"), None
    )
    if length_finding is not None and base and length_finding.rule_id not in resolved_rule_ids:
        proposed = _truncate_description(base, 800)
        resolved_rule_ids.append(length_finding.rule_id)
        explanations.append("Truncated the description to the configured character limit.")
        confidences.append(0.8)
    else:
        proposed = " ".join([base, *clauses]).strip() if base or clauses else ""

    if not resolved_rule_ids:
        return None

    return RewriteSuggestion(
        tool_name=tool.name,
        proposed_description=proposed,
        resolved_rule_ids=resolved_rule_ids,
        explanation=" ".join(explanations),
        confidence=round(min(confidences), 2),
    )


def build_suggestions(snapshot: MCPServerSnapshot, report: LintReport) -> list[RewriteSuggestion]:
    findings_by_tool: dict[str, list[Finding]] = {}
    for finding in report.findings:
        findings_by_tool.setdefault(finding.location.tool_name, []).append(finding)

    suggestions = []
    for tool in snapshot.tools:
        suggestion = suggest_for_tool(tool, findings_by_tool.get(tool.name, []))
        if suggestion is not None:
            suggestions.append(suggestion)
    return suggestions
