"""Tests for evaluation config loader."""

from pathlib import Path

from aurora.eval.config_loader import load_evaluation_config


def test_load_evaluation_config(tmp_path: Path):
    config_yaml = tmp_path / "eval.yaml"
    config_yaml.write_text(
        """
results_dir: eval/results
defaults:
  artifacts: artifacts/eval
  schedule: nightly
suites:
  swe-bench-lite:
    command: ["python", "run.py"]
    dataset: /datasets/swe-bench-lite
  swe-bench-live:
    command: ["python", "run_live.py"]
    dataset: /datasets/swe-bench-live
    schedule: weekly
    timeout_minutes: 240
""",
        encoding="utf-8",
    )

    config = load_evaluation_config(config_yaml)

    assert "swe-bench-lite" in config.suites
    suite = config.suites["swe-bench-lite"]
    assert suite.command == ["python", "run.py"]
    assert suite.schedule == "nightly"
    assert suite.timeout_minutes == 120
    assert config.results_dir == Path("eval/results")

