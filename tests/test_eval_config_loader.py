"""Tests for evaluation config loader."""

from pathlib import Path

from aurora.eval.config_loader import load_evaluation_config


def test_load_evaluation_config(tmp_path: Path):
    config_yaml = tmp_path / "eval.yaml"
    config_yaml.write_text(
        """
swe-bench-lite:
  command: ["python", "run.py"]
  dataset: /datasets/swe-bench-lite
  artifacts: artifacts/eval
""",
        encoding="utf-8",
    )

    config = load_evaluation_config(config_yaml)

    assert "swe-bench-lite" in config.suites
    suite = config.suites["swe-bench-lite"]
    assert suite.command == ["python", "run.py"]

