from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from mcplint.cli.main import app
from mcplint.mcp_client.persistence import save_snapshot
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot

runner = CliRunner()


def _snapshot_path(tmp_path: Path) -> Path:
    tool = ToolContract(
        id="a",
        name="delete_customer",
        description="Deletes a customer record.",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
        parameters=[],
        annotations=ToolAnnotation(destructive_hint=True),
        raw={},
    )
    snapshot = MCPServerSnapshot(
        metadata=ArtifactMetadata(
            schema_version="1.0",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            mcplint_version="0.1.0",
        ),
        server_name="customer-server",
        server_version=None,
        transport="stdio",
        command=None,
        tools=[tool],
    )
    path = tmp_path / "mcplint.snapshot.json"
    save_snapshot(snapshot, path)
    return path


def test_fix_prints_markdown_suggestions(tmp_path: Path) -> None:
    path = _snapshot_path(tmp_path)
    result = runner.invoke(app, ["fix", "--snapshot", str(path)])
    assert result.exit_code == 0, result.output
    assert "delete_customer" in result.output
    assert "destructive-tool-without-warning" in result.output
    assert "cannot be undone" in result.output


def test_fix_writes_output_file(tmp_path: Path) -> None:
    path = _snapshot_path(tmp_path)
    output_path = tmp_path / "fix-report.md"
    result = runner.invoke(
        app, ["fix", "--snapshot", str(path), "--output", str(output_path)]
    )
    assert result.exit_code == 0, result.output
    assert output_path.exists()
    assert "delete_customer" in output_path.read_text()


def test_fix_never_touches_source_files(tmp_path: Path) -> None:
    server_source = tmp_path / "server.py"
    server_source.write_text("# original source, must be untouched\n", encoding="utf-8")
    path = _snapshot_path(tmp_path)

    result = runner.invoke(app, ["fix", "--snapshot", str(path)])

    assert result.exit_code == 0, result.output
    assert server_source.read_text() == "# original source, must be untouched\n"


def test_fix_rejects_llm_provider() -> None:
    result = runner.invoke(
        app, ["fix", "--snapshot", "nonexistent.json", "--llm-provider", "anthropic"]
    )
    assert result.exit_code == 2
    assert "not implemented" in result.output
