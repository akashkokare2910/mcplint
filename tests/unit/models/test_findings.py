from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import SourceLocation
from mcplint.models.findings import Finding, LintReport, RuleMetadata, Severity


def _finding(severity: Severity = Severity.ERROR) -> Finding:
    return Finding(
        rule_id="missing-tool-description",
        severity=severity,
        message="Tool has no description.",
        evidence="description is None",
        location=SourceLocation(tool_name="delete_customer", json_path="$.description"),
        remediation="Add a description explaining what the tool does and when to use it.",
        confidence=1.0,
    )


def test_finding_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        Finding(
            rule_id="x",
            severity=Severity.ERROR,
            message="m",
            evidence="e",
            location=SourceLocation(tool_name="t", json_path="$"),
            remediation="r",
            confidence=1.5,
        )


def test_rule_metadata_defaults_empty_tags() -> None:
    meta = RuleMetadata(
        id="missing-tool-description",
        title="Missing tool description",
        description="Flags tools with no description.",
        default_severity=Severity.ERROR,
    )
    assert meta.tags == []


def test_lint_report_count_by_severity() -> None:
    report = LintReport(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="customer-server",
        findings=[_finding(Severity.ERROR), _finding(Severity.WARNING), _finding(Severity.ERROR)],
    )
    counts = report.count_by_severity()
    assert counts[Severity.ERROR] == 2
    assert counts[Severity.WARNING] == 1
    assert counts.get(Severity.INFO, 0) == 0
