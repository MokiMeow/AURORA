"""Tests for reward engine integration."""

from pathlib import Path

from aurora.reward import (
    RewardEngine,
    RewardCalculator,
    RewardWeights,
    MetricCollector,
    AdaptiveScheduler,
    AdaptiveWeights,
    ExperienceLogger,
)
from aurora.reward.policy import RewardPolicy


def test_reward_engine_computes_reward(tmp_path: Path):
    collector = MetricCollector()
    calculator = RewardCalculator(RewardWeights(1, 1, 1, 1, 1, 1), explainability_dir=tmp_path / "reports")
    scheduler = AdaptiveScheduler(AdaptiveWeights(1, 0.5, 0.4, 1.5, -0.3, 0.8))
    experience_logger = ExperienceLogger(tmp_path / "experience.log")
    engine = RewardEngine(
        collector=collector,
        calculator=calculator,
        scheduler=scheduler,
        experience_logger=experience_logger,
        log_path=tmp_path / "history.jsonl",
        policy=RewardPolicy(),
    )
    result = engine.compute_reward([
        {"step": "test", "success": True},
        {"step": "security", "success": True},
    ])
    assert result.reward > 0
    assert result.success is True

