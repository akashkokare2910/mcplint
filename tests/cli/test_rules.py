from typer.testing import CliRunner

from mcplint.cli.main import app

runner = CliRunner()


def test_rules_lists_all_builtin_rules() -> None:
    result = runner.invoke(app, ["rules"])
    assert result.exit_code == 0, result.output
    assert "missing-tool-description" in result.output
    assert "ambiguous-tool-overlap" in result.output
    assert "undefined-domain-term" in result.output
