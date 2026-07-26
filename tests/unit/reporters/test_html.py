from datetime import UTC, datetime

from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import SourceLocation, ToolAnnotation, ToolContract
from mcplint.models.findings import Finding, LintReport, Severity
from mcplint.models.fixes import RewriteSuggestion
from mcplint.models.snapshot import MCPServerSnapshot
from mcplint.reporters.html import render_html_report


def _tool(name: str, description: str | None) -> ToolContract:
    return ToolContract(
        id=f"id-{name}",
        name=name,
        description=description,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )


def _snapshot(*tools: ToolContract) -> MCPServerSnapshot:
    return MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="customer-server",
        server_version=None,
        transport="stdio",
        command=None,
        tools=list(tools),
    )


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


def test_render_html_report_is_self_contained_document() -> None:
    tool = _tool("get_customer", "Retrieve a customer by ID.")
    html = render_html_report(_snapshot(tool), _report([]))
    assert html.strip().startswith("<!doctype html>")
    assert "<style>" in html
    assert "customer-server" in html
    assert "get_customer" in html
    assert "<script src=" not in html
    assert "http://" not in html and "https://cdn" not in html


def test_render_html_report_shows_findings_and_score() -> None:
    tool = _tool("delete_customer", None)
    finding = Finding(
        rule_id="missing-tool-description",
        severity=Severity.ERROR,
        message="Tool has no description.",
        evidence="description is missing",
        location=SourceLocation(tool_name="delete_customer", json_path="$.description"),
        remediation="Add a description.",
        confidence=1.0,
    )
    html = render_html_report(_snapshot(tool), _report([finding]))
    assert "missing-tool-description" in html
    assert "92/100" in html


def test_render_html_report_includes_suggestions_when_given() -> None:
    tool = _tool("delete_customer", "Deletes a customer.")
    suggestion = RewriteSuggestion(
        tool_name="delete_customer",
        proposed_description="Deletes a customer. This action is permanent and cannot be undone.",
        resolved_rule_ids=["destructive-tool-without-warning"],
        explanation="Added a destructive-operation warning.",
        confidence=0.9,
    )
    html = render_html_report(_snapshot(tool), _report([]), suggestions=[suggestion])
    assert "Remediation suggestions" in html
    assert "cannot be undone" in html
