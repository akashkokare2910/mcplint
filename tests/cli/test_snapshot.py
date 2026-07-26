import sys
from pathlib import Path

from typer.testing import CliRunner

from mcplint.cli.main import app
from mcplint.mcp_client.persistence import load_snapshot

runner = CliRunner()
GOOD_SERVER = Path(__file__).parent.parent.parent / "examples" / "good_server" / "server.py"


def test_snapshot_writes_file(tmp_path: Path) -> None:
    output = tmp_path / "mcplint.snapshot.json"
    result = runner.invoke(
        app,
        ["snapshot", "--server", f"{sys.executable} {GOOD_SERVER}", "--output", str(output)],
    )
    assert result.exit_code == 0, result.output
    assert output.exists()
    snapshot = load_snapshot(output)
    assert {t.name for t in snapshot.tools} == {"get_customer", "search_customers"}
