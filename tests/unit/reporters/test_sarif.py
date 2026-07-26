import json
from datetime import UTC, datetime

from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import SourceLocation
from mcplint.models.findings import Finding, LintReport, Severity
from mcplint.reporters.sarif import render_sarif


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


def test_sarif_smoke_top_level_structure() -> None:
    payload = json.loads(render_sarif(_report([])))
    assert payload["version"] == "2.1.0"
    assert payload["$schema"].endswith("sarif-schema-2.1.0.json")
    assert len(payload["runs"]) == 1
    run = payload["runs"][0]
    assert run["tool"]["driver"]["name"] == "mcplint"
    assert isinstance(run["tool"]["driver"]["rules"], list)
    assert len(run["tool"]["driver"]["rules"]) == 15
    assert run["results"] == []


def test_sarif_smoke_result_shape() -> None:
    finding = Finding(
        rule_id="missing-tool-description",
        severity=Severity.ERROR,
        message="Tool has no description.",
        evidence="description is missing",
        location=SourceLocation(tool_name="delete_customer", json_path="$.description"),
        remediation="Add a description.",
        confidence=1.0,
    )
    payload = json.loads(render_sarif(_report([finding])))
    result = payload["runs"][0]["results"][0]
    assert result["ruleId"] == "missing-tool-description"
    assert result["level"] == "error"
    assert result["message"]["text"] == "Tool has no description."
    assert result["locations"][0]["logicalLocations"][0]["fullyQualifiedName"] == "$.description"


def test_sarif_smoke_rule_descriptor_severity_levels() -> None:
    payload = json.loads(render_sarif(_report([])))
    rules = {r["id"]: r for r in payload["runs"][0]["tool"]["driver"]["rules"]}
    assert rules["missing-tool-description"]["defaultConfiguration"]["level"] == "error"
    assert rules["excessive-description-length"]["defaultConfiguration"]["level"] == "note"
    for rule in rules.values():
        assert rule["defaultConfiguration"]["level"] in ("error", "warning", "note")
