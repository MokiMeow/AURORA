"""Tests for report CLI."""

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_report_weekly(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    metrics = tmp_path / "metrics.csv"
    dashboard = tmp_path / "dashboard.html"
    metrics.write_text("suite,success\nlite,1\n", encoding="utf-8")
    dashboard.write_text("<html></html>", encoding="utf-8")
    result = runner.invoke(
        app,
        ["report", "weekly", "--metrics", str(metrics), "--dashboard", str(dashboard)],
    )
    assert result.exit_code == 0
    report_path = Path("docs/reports/weekly_governance.md")
    assert report_path.exists()
