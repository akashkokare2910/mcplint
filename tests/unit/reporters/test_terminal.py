from datetime import UTC, datetime

from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import SourceLocation
from mcplint.models.findings import Finding, LintReport, Severity
from mcplint.reporters.terminal import render_terminal


def _report(findings: list[Finding]) -> LintReport:
    return LintReport(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="customer-server",
        findings=findings,
    )


def test_render_terminal_no_findings_reports_clean() -> None:
    output = render_terminal(_report([]))
    assert "customer-server" in output
    assert "0" in output


def test_render_terminal_lists_finding_rule_and_tool() -> None:
    finding = Finding(
        rule_id="missing-tool-description",
        severity=Severity.ERROR,
        message="Tool has no description.",
        evidence="description is missing",
        location=SourceLocation(tool_name="delete_customer", json_path="$.description"),
        remediation="Add a description.",
        confidence=1.0,
    )
    output = render_terminal(_report([finding]))
    assert "missing-tool-description" in output
    assert "delete_customer" in output
    assert "error" in output.lower()
