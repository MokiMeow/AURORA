"""Tests for autopilot CLI."""

import json
from pathlib import Path

from typer.testing import CliRunner

from aurora.autopilot import AutopilotReport
from aurora.autopilot.service import AutopilotService
from cli.main import app

runner = CliRunner()


def test_autopilot_cli(monkeypatch, tmp_path: Path) -> None:
    report = AutopilotReport(
        run_id="test",
        task="demo",
        duration_seconds=1.23,
        steps=["plan", "apply"],
        artifacts={"plan": tmp_path / "plan.json"},
        estimated_tokens=200,
    )

    def fake_run(self, task: str, dry_run: bool, require_confirm: bool, confirm_callback=None, **kwargs):  # type: ignore[no-redef]
        return report

    monkeypatch.setattr(AutopilotService, "run", fake_run)
    result = runner.invoke(
        app,
        [
            "autopilot",
            "--task",
            "demo",
            "--dry-run",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["run_id"] == "test"
