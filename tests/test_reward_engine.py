"""Tests for reward engine integration."""

from pathlib import Path

from aurora.reward import (
    AdaptiveScheduler,
    AdaptiveWeights,
    ExperienceLogger,
    MetricCollector,
    RewardCalculator,
    RewardEngine,
    RewardReportWriter,
    RewardWeights,
)
from aurora.reward.policy import RewardPolicy


def test_reward_engine_computes_reward(tmp_path: Path):
    collector = MetricCollector()
    reporter = RewardReportWriter(tmp_path / "reports", formats=("json",))
    calculator = RewardCalculator(RewardWeights(1, 1, 1, 1, 1, 1), reporter=reporter)
    scheduler = AdaptiveScheduler(AdaptiveWeights(1, 0.5, 0.4, 1.5, -0.3, 0.8))
    experience_logger = ExperienceLogger(tmp_path / "experience.log")
    engine = RewardEngine(
        collector=collector,
        calculator=calculator,
        scheduler=scheduler,
        experience_logger=experience_logger,
        history_path=tmp_path / "history.jsonl",
        policy=RewardPolicy(),
        reporter=reporter,
    )
    result = engine.compute_reward(
        [
            {"step": "pytest", "success": True, "metrics": {"tests": {"passed": 4, "failed": 0}}},
            {"step": "coverage", "success": True, "metrics": {"coverage": {"percent": 83.0, "delta": 0.2}}},
            {"step": "security", "success": True},
        ]
    )
    assert result.reward > 0
    assert result.success is True
    assert "tests" in result.components
    assert isinstance(result.timestamp, str)


