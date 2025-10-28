"""Tests for reward configuration loader."""

from pathlib import Path

from aurora.reward import load_reward_config


def test_load_reward_config(tmp_path: Path) -> None:
    config_path = tmp_path / "reward.yaml"
    config_path.write_text(
        """
weights:
  tests: 2.0
  coverage: 0.6
  perf: 0.3
  security: 1.8
  complexity: -0.4
  policy: 0.9
adaptive_scheduler:
  window_runs: 10
  min_weight: 0.1
  max_weight: 3.0
  adjust_on:
    - failing_tests
    - coverage_regressions
  strategy: epsilon_greedy
  explore_probability: 0.2
bias_penalty:
  enabled: true
  max_delta: 0.04
  penalty_weight: 3.1
explainability:
  store_path: reports
  formats:
    - json
    - html
  keep_last: 5
  enable_timeline: false
  history_filename: custom_history.jsonl
  trend_filename: custom_trend.html
acceptance:
  min_reward: 0.5
  require_security_pass: true
  max_bias: 0.02
  enforce_explainability: false
experience_vault:
  log_path: logs/log.jsonl
  index_root: logs/index
  max_records: 100
  retention_days: 30
  dedupe_fields:
    - task
    - diff_hash
  redact_fields:
    - token
  compress: true
regression_suite:
  enabled: false
  fixtures_path: fixtures
  tolerance: 0.1
""",
        encoding="utf-8",
    )

    config = load_reward_config(tmp_path, config_path)

    assert config.weights.tests == 2.0
    assert config.scheduler.strategy == "epsilon_greedy"
    assert set(config.scheduler.adjust_on) == {"failing_tests", "coverage_regressions"}
    assert config.adaptive_weights.tests == config.weights.tests
    assert config.bias_penalty.penalty_weight == 3.1
    assert config.explainability.store_path == tmp_path / "reports"
    assert tuple(config.explainability.formats) == ("json", "html")
    assert config.explainability.keep_last == 5
    assert config.acceptance.enforce_explainability is False
    assert config.experience_vault.compress is True
    assert config.regression.enabled is False
    assert config.regression.fixtures_path == tmp_path / "fixtures"
