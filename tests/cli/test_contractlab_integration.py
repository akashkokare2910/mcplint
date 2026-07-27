"""End-to-end ContractLab pipeline against a real, live MCP server.

Runs validate -> generate-benchmark -> mutate -> confusion in sequence,
each command consuming the previous command's actual output file, against
the intentionally-ambiguous example server. Uses --provider fake throughout:
this proves the four features compose through real files and the existing
snapshot/benchmark machinery, not that any particular model behaves well.
"""

from __future__ import annotations

import sys
from pathlib import Path

from typer.testing import CliRunner

from mcplint.cli.main import app

runner = CliRunner()
EXAMPLE_DIR = Path(__file__).parent.parent.parent / "examples" / "ambiguous_customer_server"
SERVER = EXAMPLE_DIR / "server.py"
CONTRACT = EXAMPLE_DIR / "mcplint.contract.yaml"
DATASET = EXAMPLE_DIR / "customer-tools.evals.yaml"


def test_full_contractlab_pipeline(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_result = runner.invoke(
        app,
        [
            "snapshot",
            "--server",
            f"{sys.executable} {SERVER}",
            "--output",
            str(snapshot_path),
        ],
    )
    assert snapshot_result.exit_code == 0, snapshot_result.output

    validate_result = runner.invoke(
        app, ["contract", "validate", str(CONTRACT), "--snapshot", str(snapshot_path)]
    )
    assert validate_result.exit_code == 0, validate_result.output
    assert "consistent" in validate_result.output

    adversarial_path = tmp_path / "adversarial.evals.yaml"
    generate_result = runner.invoke(
        app,
        [
            "contract",
            "generate-benchmark",
            str(CONTRACT),
            "--snapshot",
            str(snapshot_path),
            "--output",
            str(adversarial_path),
        ],
    )
    assert generate_result.exit_code == 0, generate_result.output
    assert adversarial_path.exists()

    mutate_result = runner.invoke(
        app,
        [
            "contract",
            "mutate",
            str(CONTRACT),
            "--snapshot",
            str(snapshot_path),
            "--dataset",
            str(adversarial_path),
            "--provider",
            "fake",
            "--runs",
            "1",
        ],
    )
    assert mutate_result.exit_code == 0, mutate_result.output
    assert "mutation(s) tested" in mutate_result.output

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

    confusion_result = runner.invoke(
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
    assert confusion_result.exit_code == 0, confusion_result.output
    assert "flagged pair(s)" in confusion_result.output
