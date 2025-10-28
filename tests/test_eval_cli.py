"""Tests for evaluation CLI commands."""

import json
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_eval_compare(tmp_path: Path):
    run_a = tmp_path / "run_a.json"
    run_b = tmp_path / "run_b.json"
    run_a.write_text(json.dumps({"success_rate": 0.5}), encoding="utf-8")
    run_b.write_text(json.dumps({"success_rate": 0.7}), encoding="utf-8")
    result = runner.invoke(app, ["eval", "compare", str(run_a), str(run_b)])
    assert result.exit_code == 0
    assert "success_rate" in result.stdout


def test_eval_report(tmp_path: Path):
    config_path = tmp_path / "eval.yaml"
    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    metrics_file = results_dir / "lite_001_metrics.json"
    metrics_file.write_text(json.dumps({"suite": "lite", "run_id": "001", "success_rate": 1.0}), encoding="utf-8")
    config_path.write_text(
        f"""
results_dir: {results_dir.as_posix()}
dataset_manager:
  cache_dir: { (tmp_path / "cache").as_posix() }
  manifest_path: { (tmp_path / "cache" / "manifest.json").as_posix() }
  auto_update: false
  ttl_hours: 1
analytics:
  metrics_csv: { (tmp_path / "metrics.csv").as_posix() }
  dashboard_html: { (tmp_path / "dashboard.html").as_posix() }
  compare_dir: { (tmp_path / "compare").as_posix() }
suites:
  lite:
    command: ["python", "run.py"]
    dataset: { (tmp_path / "datasets").as_posix() }
""",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["eval", "report", "--config", str(config_path), "--suite", "lite", "--limit", "1", "--skip-dashboard"])
    assert result.exit_code == 0
    assert "lite" in result.stdout
