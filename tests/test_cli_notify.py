"""Tests for notify CLI."""

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_notify_slack(tmp_path: Path) -> None:
    config = tmp_path / "notify.yaml"
    log_path = tmp_path / "notify.log"
    config.write_text(
        f"channels:\n  slack:\n    webhook: https://example.com\n  email:\n    recipients: ['ops@example.com']\n  webhook:\n    endpoint: https://example.com/hook\nlog_path: {log_path.as_posix()}\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["notify", "slack", "Deployment ready", "--config", str(config)])
    assert result.exit_code == 0
    assert log_path.exists()
    assert "Deployment ready" in log_path.read_text(encoding="utf-8")
