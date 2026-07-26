"""Render a LintReport as SARIF 2.1.0 for GitHub code scanning / CI upload."""

from __future__ import annotations

import json

from mcplint.__about__ import __version__ as MCPLINT_VERSION
from mcplint.core.registry import RuleRegistry
from mcplint.models.findings import Finding, LintReport, Severity

SARIF_SCHEMA_URI = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
)
SARIF_VERSION = "2.1.0"
MCPLINT_INFORMATION_URI = "https://github.com/mcplint/mcplint"

_LEVEL_BY_SEVERITY = {Severity.ERROR: "error", Severity.WARNING: "warning", Severity.INFO: "note"}


def _rule_descriptors() -> list[dict[str, object]]:
    registry = RuleRegistry.with_builtin_rules()
    descriptors: list[dict[str, object]] = []
    for rule in registry.all():
        metadata = rule.metadata()
        descriptors.append(
            {
                "id": metadata.id,
                "name": metadata.id,
                "shortDescription": {"text": metadata.title},
                "fullDescription": {"text": metadata.description},
                "defaultConfiguration": {"level": _LEVEL_BY_SEVERITY[metadata.default_severity]},
                "properties": {"tags": list(metadata.tags)},
            }
        )
    return descriptors


def _result(finding: Finding) -> dict[str, object]:
    return {
        "ruleId": finding.rule_id,
        "level": _LEVEL_BY_SEVERITY[finding.severity],
        "message": {"text": finding.message},
        "properties": {
            "evidence": finding.evidence,
            "remediation": finding.remediation,
            "confidence": finding.confidence,
        },
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": f"mcp-tool:{finding.location.tool_name}"},
                },
                "logicalLocations": [{"fullyQualifiedName": finding.location.json_path}],
            }
        ],
    }


def render_sarif(report: LintReport) -> str:
    sarif_log = {
        "$schema": SARIF_SCHEMA_URI,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "mcplint",
                        "informationUri": MCPLINT_INFORMATION_URI,
                        "version": MCPLINT_VERSION,
                        "rules": _rule_descriptors(),
                    }
                },
                "results": [_result(finding) for finding in report.findings],
            }
        ],
    }
    return json.dumps(sarif_log, indent=2)
