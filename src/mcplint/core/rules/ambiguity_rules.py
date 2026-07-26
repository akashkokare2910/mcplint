"""Rules built on top of the cross-tool ambiguity engine (`ambiguity.py`).

Both rules iterate every *other* tool in the snapshot but only emit a
finding once per unordered pair (when `tool.name < other.name`), since the
lint engine calls `check()` once per tool and pairs would otherwise be
reported twice.
"""

from __future__ import annotations

from mcplint.core.rules.ambiguity import DEFAULT_AMBIGUITY_THRESHOLD, compute_ambiguity
from mcplint.core.rules.base import Rule, RuleContext
from mcplint.models.contracts import SourceLocation, ToolContract
from mcplint.models.findings import Finding, Severity


class AmbiguousToolOverlapRule(Rule):
    id = "ambiguous-tool-overlap"
    title = "Ambiguous tool overlap"
    description = (
        "Flags pairs of tools whose name, description, and parameters overlap "
        "enough that an agent could plausibly pick either one for the same task."
    )
    default_severity = Severity.WARNING
    tags = ("ambiguity",)
    threshold = DEFAULT_AMBIGUITY_THRESHOLD

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        findings = []
        for other in context.snapshot.tools:
            if other.name <= tool.name:
                continue
            result = compute_ambiguity(tool, other)
            if result.score < self.threshold:
                continue
            evidence_parts = [f"ambiguity score {result.score:.2f} (threshold {self.threshold:.2f})"]
            if result.evidence.shared_verbs:
                evidence_parts.append(f"shared verbs: {', '.join(result.evidence.shared_verbs)}")
            if result.evidence.shared_entities:
                evidence_parts.append(f"shared entities: {', '.join(result.evidence.shared_entities)}")
            if result.evidence.overlapping_parameters:
                evidence_parts.append(
                    f"overlapping parameters: {', '.join(result.evidence.overlapping_parameters)}"
                )
            findings.append(
                Finding(
                    rule_id=self.id,
                    severity=self.default_severity,
                    message=f"Tools '{tool.name}' and '{other.name}' are semantically ambiguous.",
                    evidence="; ".join(evidence_parts),
                    location=SourceLocation(tool_name=tool.name, json_path="$.description"),
                    remediation=(
                        f"Clarify how '{tool.name}' differs from '{other.name}': when an "
                        "agent should pick one over the other."
                    ),
                    confidence=min(0.9, 0.4 + result.score / 2),
                )
            )
        return findings


class MissingToolDistinctionRule(Rule):
    id = "missing-tool-distinction"
    title = "Missing tool distinction"
    description = (
        "For ambiguous tool pairs, flags the absence of an explicit "
        "exact-vs-search, one-vs-many, or read-vs-write distinction."
    )
    default_severity = Severity.INFO
    tags = ("ambiguity",)
    threshold = DEFAULT_AMBIGUITY_THRESHOLD

    def check(self, tool: ToolContract, context: RuleContext) -> list[Finding]:
        findings = []
        for other in context.snapshot.tools:
            if other.name <= tool.name:
                continue
            result = compute_ambiguity(tool, other)
            if result.score < self.threshold or not result.has_missing_distinction():
                continue
            missing = []
            if result.evidence.absent_exact_vs_search_distinction:
                missing.append("exact-vs-search")
            if result.evidence.absent_one_vs_many_distinction:
                missing.append("one-vs-many")
            if result.evidence.absent_read_vs_write_distinction:
                missing.append("read-vs-write")
            findings.append(
                Finding(
                    rule_id=self.id,
                    severity=self.default_severity,
                    message=(
                        f"Tools '{tool.name}' and '{other.name}' don't state a "
                        f"{'/'.join(missing)} distinction."
                    ),
                    evidence=f"missing distinction(s): {', '.join(missing)}",
                    location=SourceLocation(tool_name=tool.name, json_path="$.description"),
                    remediation=(
                        f"Add a sentence like \"Use {tool.name} when ... Use {other.name} "
                        f'when ..." to both descriptions.'
                    ),
                    confidence=0.5,
                )
            )
        return findings
