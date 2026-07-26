import sys
from pathlib import Path

from typer.testing import CliRunner

from mcplint.cli.main import app

runner = CliRunner()
GOOD_SERVER = Path(__file__).parent.parent.parent / "examples" / "good_server" / "server.py"


def test_inspect_lists_tools() -> None:
    result = runner.invoke(app, ["inspect", "--server", f"{sys.executable} {GOOD_SERVER}"])
    assert result.exit_code == 0, result.output
    assert "get_customer" in result.output
    assert "search_customers" in result.output


def test_inspect_fails_on_bad_command() -> None:
    result = runner.invoke(app, ["inspect", "--server", "this-command-does-not-exist"])
    assert result.exit_code == 1
