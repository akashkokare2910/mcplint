import sys
from pathlib import Path

from typer.testing import CliRunner

from mcplint.cli.main import app

runner = CliRunner()
AMBIGUOUS_SERVER = (
    Path(__file__).parent.parent.parent / "examples" / "ambiguous_customer_server" / "server.py"
)
DATASET = (
    Path(__file__).parent.parent.parent
    / "examples"
    / "ambiguous_customer_server"
    / "customer-tools.evals.yaml"
)


def _snapshot_and_result(tmp_path: Path) -> tuple[Path, Path]:
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_result = runner.invoke(
        app,
        [
            "snapshot",
            "--server",
            f"{sys.executable} {AMBIGUOUS_SERVER}",
            "--output",
            str(snapshot_path),
        ],
    )
    assert snapshot_result.exit_code == 0, snapshot_result.output

    result_path = tmp_path / "result.json"
    benchmark_result = runner.invoke(
        app,
        [
            "benchmark",
            str(DATASET),
            "--snapshot",
            str(snapshot_path),
            "--provider",
            "fake",
            "--runs",
            "1",
            "--format",
            "json",
            "--output",
            str(result_path),
        ],
    )
    assert benchmark_result.exit_code == 0, benchmark_result.output
    return snapshot_path, result_path


def test_confusion_reports_flagged_pairs(tmp_path: Path) -> None:
    snapshot_path, result_path = _snapshot_and_result(tmp_path)

    result = runner.invoke(
        app,
        [
            "confusion",
            "--result",
            str(result_path),
            "--dataset",
            str(DATASET),
            "--snapshot",
            str(snapshot_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "flagged pair(s)" in result.output


def test_confusion_json_output_and_file(tmp_path: Path) -> None:
    snapshot_path, result_path = _snapshot_and_result(tmp_path)
    output_path = tmp_path / "confusion.json"

    result = runner.invoke(
        app,
        [
            "confusion",
            "--result",
            str(result_path),
            "--dataset",
            str(DATASET),
            "--snapshot",
            str(snapshot_path),
            "--format",
            "json",
            "--output",
            str(output_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert output_path.exists()
    assert '"dataset_name"' in output_path.read_text()


def test_confusion_missing_result_file(tmp_path: Path) -> None:
    snapshot_path, _ = _snapshot_and_result(tmp_path)

    result = runner.invoke(
        app,
        [
            "confusion",
            "--result",
            str(tmp_path / "missing.json"),
            "--dataset",
            str(DATASET),
            "--snapshot",
            str(snapshot_path),
        ],
    )
    assert result.exit_code == 2


def test_confusion_missing_dataset_file(tmp_path: Path) -> None:
    snapshot_path, result_path = _snapshot_and_result(tmp_path)

    result = runner.invoke(
        app,
        [
            "confusion",
            "--result",
            str(result_path),
            "--dataset",
            str(tmp_path / "missing.evals.yaml"),
            "--snapshot",
            str(snapshot_path),
        ],
    )
    assert result.exit_code == 2
