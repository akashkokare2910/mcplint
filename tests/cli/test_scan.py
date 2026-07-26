import sys
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from mcplint.cli.main import app
from mcplint.mcp_client.persistence import save_snapshot
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot

runner = CliRunner()
GOOD_SERVER = Path(__file__).parent.parent.parent / "examples" / "good_server" / "server.py"


def _bad_snapshot_path(tmp_path: Path) -> Path:
    tool = ToolContract(
        id="a",
        name="delete_customer",
        description=None,
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(),
        raw={},
    )
    snapshot = MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="bad-server",
        server_version=None,
        transport="stdio",
        command=None,
        tools=[tool],
    )
    path = tmp_path / "bad.snapshot.json"
    save_snapshot(snapshot, path)
    return path


def test_scan_snapshot_with_findings_exits_1_by_default(tmp_path: Path) -> None:
    path = _bad_snapshot_path(tmp_path)
    result = runner.invoke(app, ["scan", "--snapshot", str(path)])
    assert result.exit_code == 1
    assert "missing-tool-description" in result.output


def test_scan_snapshot_fail_on_never_exits_0(tmp_path: Path) -> None:
    path = _bad_snapshot_path(tmp_path)
    result = runner.invoke(app, ["scan", "--snapshot", str(path), "--fail-on", "never"])
    assert result.exit_code == 0


def test_scan_snapshot_json_format(tmp_path: Path) -> None:
    path = _bad_snapshot_path(tmp_path)
    result = runner.invoke(
        app, ["scan", "--snapshot", str(path), "--format", "json", "--fail-on", "never"]
    )
    assert result.exit_code == 0
    assert '"rule_id": "missing-tool-description"' in result.output


def test_scan_snapshot_sarif_format(tmp_path: Path) -> None:
    path = _bad_snapshot_path(tmp_path)
    result = runner.invoke(
        app, ["scan", "--snapshot", str(path), "--format", "sarif", "--fail-on", "never"]
    )
    assert result.exit_code == 0
    assert '"version": "2.1.0"' in result.output
    assert '"ruleId": "missing-tool-description"' in result.output


def test_scan_snapshot_html_format_writes_output(tmp_path: Path) -> None:
    path = _bad_snapshot_path(tmp_path)
    output_path = tmp_path / "report.html"
    result = runner.invoke(
        app,
        [
            "scan",
            "--snapshot",
            str(path),
            "--format",
            "html",
            "--fail-on",
            "never",
            "--output",
            str(output_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert output_path.exists()
    html = output_path.read_text()
    assert html.strip().startswith("<!doctype html>")
    assert "missing-tool-description" in html


def test_scan_live_server_clean() -> None:
    result = runner.invoke(app, ["scan", "--server", f"{sys.executable} {GOOD_SERVER}"])
    assert result.exit_code == 0, result.output


def test_scan_requires_server_or_snapshot() -> None:
    result = runner.invoke(app, ["scan"])
    assert result.exit_code != 0
