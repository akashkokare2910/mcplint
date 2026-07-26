"""Pure function that runs every registered rule over every tool in a snapshot."""

from __future__ import annotations

from mcplint.core.registry import RuleRegistry
from mcplint.core.rules.base import RuleContext
from mcplint.models.common import ArtifactMetadata
from mcplint.models.findings import Finding, LintReport
from mcplint.models.snapshot import MCPServerSnapshot

REPORT_SCHEMA_VERSION = "1.0"


def lint_snapshot(snapshot: MCPServerSnapshot, registry: RuleRegistry) -> LintReport:
    context = RuleContext(snapshot=snapshot)
    findings: list[Finding] = []
    for tool in snapshot.tools:
        for rule in registry.all():
            findings.extend(rule.check(tool, context))
    return LintReport(
        metadata=ArtifactMetadata.create(schema_version=REPORT_SCHEMA_VERSION),
        server_name=snapshot.server_name,
        findings=findings,
    )
