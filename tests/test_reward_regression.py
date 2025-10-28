"""Tests for reward regression suite."""

from pathlib import Path

from aurora.reward import (
    AdaptiveScheduler,
    AdaptiveWeights,
    ExperienceLogger,
    MetricCollector,
    RegressionSuiteConfig,
    RewardCalculator,
    RewardEngine,
    RewardReportWriter,
    RewardWeights,
)
from aurora.reward.policy import RewardPolicy


class DummyMetrics:
    def record_reward(self, suite: str, reward: float) -> None:
        pass


def test_reward_engine_regression_suite_matches(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    fixture = fixture_dir / "case.json"
    fixture.write_text(
        """
{
  "name": "ci_success",
  "expected_reward": 6.9,
  "ci_results": [
    {
      "suite": "ci",
      "metrics": {
        "tests": {"passed": 5, "failed": 0},
        "coverage": {"percent": 85.0, "delta": 0.3},
        "performance": {"p95_ms": 420, "delta_ms": 0.2},
        "security": {"score": 1.0, "findings": 0},
        "complexity": {"delta": -0.1},
        "policy": {"bonus": 0.5},
        "bias": {"score": 0.02}
      }
    }
  ]
}
        """.strip(),
        encoding="utf-8",
    )
    reporter = RewardReportWriter(tmp_path / "reports", formats=("json",))
    engine = RewardEngine(
        collector=MetricCollector(),
        calculator=RewardCalculator(RewardWeights(1, 1, 1, 1, 1, 1), reporter=reporter),
        scheduler=AdaptiveScheduler(AdaptiveWeights(1, 1, 1, 1, 1, 1)),
        experience_logger=ExperienceLogger(tmp_path / "experience.log"),
        history_path=tmp_path / "history.jsonl",
        policy=RewardPolicy(),
        reporter=reporter,
        metrics_emitter=DummyMetrics(),
        regression=RegressionSuiteConfig(enabled=True, fixtures_path=fixture_dir, tolerance=0.2),
    )

    mismatches = engine.run_regression_suite()
    assert mismatches == []
