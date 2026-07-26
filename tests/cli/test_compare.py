from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from mcplint.cli.main import app
from mcplint.mcp_client.persistence import save_snapshot
from mcplint.models.common import ArtifactMetadata
from mcplint.models.contracts import ToolAnnotation, ToolContract
from mcplint.models.snapshot import MCPServerSnapshot

runner = CliRunner()
DATASET = (
    Path(__file__).parent.parent.parent
    / "examples"
    / "ambiguous_customer_server"
    / "customer-tools.evals.yaml"
)


def _snapshot_path(tmp_path: Path, filename: str, description: str | None) -> Path:
    tool = ToolContract(
        id="a",
        name="get_customer",
        description=description,
        input_schema={
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
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
        server_name="customer-server",
        server_version=None,
        transport="stdio",
        command=None,
        tools=[tool],
    )
    path = tmp_path / filename
    save_snapshot(snapshot, path)
    return path


def test_compare_reports_resolved_finding(tmp_path: Path) -> None:
    baseline = _snapshot_path(tmp_path, "baseline.json", None)
    candidate = _snapshot_path(
        tmp_path,
        "candidate.json",
        "Retrieve a single customer record by its exact customer identifier. "
        "Returns the customer's profile fields as JSON. Raises an error if "
        "the identifier does not exist.",
    )
    result = runner.invoke(
        app, ["compare", "--baseline", str(baseline), "--candidate", str(candidate)]
    )
    assert result.exit_code == 0, result.output
    assert "resolved" in result.output.lower()


def test_compare_with_dataset_and_min_accuracy_delta(tmp_path: Path) -> None:
    baseline = _snapshot_path(tmp_path, "baseline.json", "Get a customer.")
    candidate = _snapshot_path(tmp_path, "candidate.json", "Get a customer.")
    result = runner.invoke(
        app,
        [
            "compare",
            "--baseline",
            str(baseline),
            "--candidate",
            str(candidate),
            "--dataset",
            str(DATASET),
            "--provider",
            "fake",
            "--runs",
            "1",
            "--min-accuracy-delta",
            "-0.5",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Benchmark: customer-tools" in result.output


def test_compare_missing_snapshot_exits_2(tmp_path: Path) -> None:
    candidate = _snapshot_path(tmp_path, "candidate.json", "Get a customer.")
    result = runner.invoke(
        app,
        ["compare", "--baseline", str(tmp_path / "missing.json"), "--candidate", str(candidate)],
    )
    assert result.exit_code == 2
