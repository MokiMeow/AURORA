"""Tests for evaluation config loader."""

from pathlib import Path

from aurora.eval.config_loader import load_evaluation_config


def test_load_evaluation_config(tmp_path: Path):
    config_yaml = tmp_path / "eval.yaml"
    config_yaml.write_text(
        """
results_dir: eval/results
dataset_manager:
  cache_dir: cache
  manifest_path: cache/manifest.json
  auto_update: false
  ttl_hours: 12
  download_base_url: https://example.com/datasets
analytics:
  metrics_csv: eval/metrics.csv
  dashboard_html: docs/reports/dashboard.html
  compare_dir: eval/compare
defaults:
  artifacts: artifacts/eval
  schedule: nightly
  scenarios: 10
  postprocessors:
    - scripts/post/process.py
suites:
  swe-bench-lite:
    command: ["python", "run.py"]
    dataset: /datasets/swe-bench-lite
    baseline_metrics: baselines/lite.json
  swe-bench-live:
    command: ["python", "run_live.py"]
    dataset: /datasets/swe-bench-live
    schedule: weekly
    timeout_minutes: 240
    compare_against: swe-bench-lite
""",
        encoding="utf-8",
    )

    config = load_evaluation_config(config_yaml)

    assert "swe-bench-lite" in config.suites
    suite = config.suites["swe-bench-lite"]
    assert suite.command == ["python", "run.py"]
    assert suite.schedule == "nightly"
    assert suite.timeout_minutes == 120
    assert suite.scenarios == 10
    assert suite.baseline_metrics == Path("baselines/lite.json")
    assert suite.postprocessors == ("scripts/post/process.py",)
    assert config.dataset_manager.cache_dir == Path("cache")
    assert config.dataset_manager.auto_update is False
    assert config.analytics.metrics_csv == Path("eval/metrics.csv")
    assert config.results_dir == Path("eval/results")

