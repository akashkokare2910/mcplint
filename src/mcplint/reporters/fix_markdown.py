"""Render RewriteSuggestions as a Markdown patch report: never applied automatically."""

from __future__ import annotations

from mcplint.models.fixes import RewriteSuggestion


def render_fix_markdown(server_name: str, suggestions: list[RewriteSuggestion]) -> str:
    lines = [f"# MCPLint fix suggestions for `{server_name}`", ""]

    if not suggestions:
        lines.append("No actionable suggestions: nothing to fix.")
        return "\n".join(lines) + "\n"

    lines.append(
        "These are proposed changes only. MCPLint never overwrites source files "
        "automatically: review and apply them by hand."
    )
    lines.append("")

    for suggestion in suggestions:
        lines.append(f"## `{suggestion.tool_name}`")
        lines.append("")
        lines.append(f"**Confidence:** {suggestion.confidence:.2f}")
        lines.append(f"**Resolves:** {', '.join(f'`{r}`' for r in suggestion.resolved_rule_ids)}")
        lines.append("")
        lines.append("**Proposed description:**")
        lines.append("")
        lines.append(f"> {suggestion.proposed_description}")
        lines.append("")
        lines.append(f"**Why:** {suggestion.explanation}")
        lines.append("")

    return "\n".join(lines) + "\n"
