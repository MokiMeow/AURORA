"""Tests for executor config loader."""

from pathlib import Path

from aurora.executor.config_loader import load_executor_config


def test_load_executor_config(tmp_path: Path):
    ci_yaml = tmp_path / "ci.yaml"
    ci_yaml.write_text(
        """
fast:
  steps:
    - name: lint
      command: "echo lint"
  timeout_minutes: 10
  fail_fast: true
""",
        encoding="utf-8",
    )

    config = load_executor_config(tmp_path, ci_yaml)

    assert "fast" in config.profiles
    assert config.profiles["fast"].steps[0].name == "lint"

