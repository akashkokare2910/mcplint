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


def test_benchmark_runs_fake_provider_against_live_server() -> None:
    result = runner.invoke(
        app,
        [
            "benchmark",
            str(DATASET),
            "--server",
            f"{sys.executable} {AMBIGUOUS_SERVER}",
            "--provider",
            "fake",
            "--runs",
            "2",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "customer-tools" in result.output
    assert "Exact tool-selection accuracy" in result.output


def test_benchmark_json_output_and_file(tmp_path: Path) -> None:
    output_path = tmp_path / "result.json"
    result = runner.invoke(
        app,
        [
            "benchmark",
            str(DATASET),
            "--server",
            f"{sys.executable} {AMBIGUOUS_SERVER}",
            "--provider",
            "fake",
            "--runs",
            "1",
            "--format",
            "json",
            "--output",
            str(output_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert output_path.exists()
    assert '"dataset_name": "customer-tools"' in output_path.read_text()


def test_benchmark_rejects_unimplemented_provider() -> None:
    result = runner.invoke(
        app,
        [
            "benchmark",
            str(DATASET),
            "--server",
            f"{sys.executable} {AMBIGUOUS_SERVER}",
            "--provider",
            "anthropic",
        ],
    )
    assert result.exit_code == 2
    assert "not implemented" in result.output


def test_benchmark_requires_server_or_snapshot() -> None:
    result = runner.invoke(app, ["benchmark", str(DATASET)])
    assert result.exit_code == 2
