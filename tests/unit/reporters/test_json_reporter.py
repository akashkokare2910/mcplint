import json
from datetime import UTC, datetime

from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import SourceLocation
from mcplint.models.findings import Finding, LintReport, Severity
from mcplint.reporters.json_reporter import render_json


def test_render_json_roundtrips_findings() -> None:
    finding = Finding(
        rule_id="missing-tool-description",
        severity=Severity.ERROR,
        message="Tool has no description.",
        evidence="description is missing",
        location=SourceLocation(tool_name="delete_customer", json_path="$.description"),
        remediation="Add a description.",
        confidence=1.0,
    )
    report = LintReport(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="customer-server",
        findings=[finding],
    )
    payload = json.loads(render_json(report))
    assert payload["server_name"] == "customer-server"
    assert payload["findings"][0]["rule_id"] == "missing-tool-description"
    assert payload["findings"][0]["severity"] == "error"
