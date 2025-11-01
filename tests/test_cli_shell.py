"""Tests for shell CLI."""

from typer.testing import CliRunner

from cli.main import app


runner = CliRunner()


def test_shell_script_mode() -> None:
    result = runner.invoke(app, ["shell", "--script", "/context;/allow autopilot;exit"])
    assert result.exit_code == 0
    assert "Approvals" in result.stdout
    assert "allow set" in result.stdout
