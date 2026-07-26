"""Pure function that runs every registered rule over every tool in a snapshot."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcplint.core.registry import RuleRegistry
from mcplint.core.rules.base import RuleContext
from mcplint.models.common import ArtifactMetadata
from mcplint.models.findings import Finding, LintReport
from mcplint.models.snapshot import MCPServerSnapshot

if TYPE_CHECKING:
    from mcplint.config.schema import MCPLintConfig

REPORT_SCHEMA_VERSION = "1.0"


def lint_snapshot(
    snapshot: MCPServerSnapshot,
    registry: RuleRegistry,
    config: "MCPLintConfig | None" = None,
) -> LintReport:
    context = RuleContext(snapshot=snapshot)
    all_rule_ids = {rule.id for rule in registry.all()}
    findings: list[Finding] = []
    for tool in snapshot.tools:
        ignored = config.ignored_rule_ids_for_tool(tool.name, all_rule_ids) if config else set()
        for rule in registry.all():
            if rule.id in ignored:
                continue
            for finding in rule.check(tool, context):
                if config and rule.id in config.severity:
                    finding = finding.model_copy(update={"severity": config.severity[rule.id]})
                findings.append(finding)
    return LintReport(
        metadata=ArtifactMetadata.create(schema_version=REPORT_SCHEMA_VERSION),
        server_name=snapshot.server_name,
        findings=findings,
    )
