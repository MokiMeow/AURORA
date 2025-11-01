"""Tests for API CLI."""

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_api_lifecycle(tmp_path: Path) -> None:
    state_path = tmp_path / "server.json"
    start = runner.invoke(app, ["api", "start", "--port", "9090", "--state-path", str(state_path)])
    assert start.exit_code == 0
    assert state_path.exists()
    status = runner.invoke(app, ["api", "status", "--state-path", str(state_path)])
    assert status.exit_code == 0
    stop = runner.invoke(app, ["api", "stop", "--state-path", str(state_path)])
    assert stop.exit_code == 0
