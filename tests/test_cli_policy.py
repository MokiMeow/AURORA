"""Tests for policy CLI."""

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_policy_list_set_check(tmp_path: Path) -> None:
    config = Path("configs/policy_profiles.yaml")
    assert config.exists()
    active_path = tmp_path / "active.txt"
    list_result = runner.invoke(app, ["policy", "list", "--config", str(config)])
    assert list_result.exit_code == 0
    set_result = runner.invoke(
        app,
        ["policy", "set", "baseline", "--config", str(config), "--active-path", str(active_path)],
    )
    assert set_result.exit_code == 0
    check_result = runner.invoke(
        app,
        ["policy", "check", "--profile", "baseline", "--config", str(config)],
    )
    assert check_result.exit_code == 0
    assert '"accepted": true' in check_result.stdout
