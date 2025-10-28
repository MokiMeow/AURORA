"""Tests for reward service wiring."""

from pathlib import Path

from aurora.reward import RewardService
class DummyMetrics:
    started = True

    def record_reward(self, suite: str, reward: float) -> None:
        pass


def write_config(path: Path) -> None:
    path.write_text(
        """
weights:
  tests: 1.0
  coverage: 0.5
  perf: 0.2
  security: 1.2
  complexity: -0.1
  policy: 0.7
adaptive_scheduler:
  window_runs: 5
  min_weight: 0.1
  max_weight: 2.0
  adjust_on: []
  strategy: windowed
  explore_probability: 0.0
  reward_floor: 0.0
bias_penalty:
  enabled: true
  max_delta: 0.05
  penalty_weight: 2.0
explainability:
  store_path: artifacts/reward_reports
  formats: [json]
  keep_last: 5
  enable_timeline: false
  history_filename: reward_history.jsonl
  trend_filename: reward_trend.html
acceptance:
  min_reward: -1.0
  require_security_pass: false
  max_bias: 0.1
  enforce_explainability: false
experience_vault:
  log_path: experience/reward.log.jsonl
  index_root: experience/indices
  max_records: 100
  retention_days: 30
  dedupe_fields: [task]
  redact_fields: []
  compress: false
regression_suite:
  enabled: false
  fixtures_path: tests/fixtures/reward_runs
  tolerance: 0.5
""",
        encoding="utf-8",
    )


def test_reward_service_evaluate(tmp_path: Path) -> None:
    config_path = tmp_path / "reward.yaml"
    write_config(config_path)

    ci_results = [
        {
            "suite": "ci",
            "metrics": {
                "tests": {"passed": 4, "failed": 0},
                "coverage": {"percent": 80, "delta": 0.2},
                "security": {"score": 1.0, "findings": 0},
                "bias": {"score": 0.01},
            },
        }
    ]

    service = RewardService.from_config(
        config_path=config_path,
        root=tmp_path,
        metrics_emitter=DummyMetrics(),
    )
    result = service.evaluate(ci_results)
    assert result.reward > 0

    history = service.history(limit=1)
    assert history
    assert history[0]["reward"] == result.reward

    summary = service.summary()
    assert summary["count"] >= 1
