"""Tests for workspace CLI."""

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_workspace_snapshot_and_status(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    snapshot = runner.invoke(app, ["workspace", "snapshot", "--tag", "test"])
    assert snapshot.exit_code == 0
    status = runner.invoke(app, ["workspace", "status"])
    assert status.exit_code == 0
    assert '"count": 1' in status.stdout
