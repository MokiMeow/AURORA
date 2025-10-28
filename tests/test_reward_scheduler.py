"""Tests for adaptive scheduler strategies."""

from aurora.reward import AdaptiveScheduler, AdaptiveWeights


def test_adaptive_scheduler_ucb_increases_high_value_component():
    scheduler = AdaptiveScheduler(
        AdaptiveWeights(1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
        strategy="ucb1",
        history_window=5,
    )
    records = [
        {"reward": 1.2, "components": {"tests": 0.8, "coverage": 0.1}, "metrics": {}},
        {"reward": 1.1, "components": {"tests": 0.6, "coverage": 0.2}, "metrics": {}},
    ]
    scheduler.adjust(records)
    assert scheduler.weights.tests > 1.0
    assert scheduler.weights.coverage <= 1.0


def test_adaptive_scheduler_epsilon_explores(monkeypatch):
    scheduler = AdaptiveScheduler(
        AdaptiveWeights(1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
        strategy="epsilon_greedy",
        explore_probability=1.0,
    )
    monkeypatch.setattr("aurora.reward.adaptive.random.choice", lambda seq: "coverage")
    scheduler.adjust([{"reward": 0.5, "components": {}, "metrics": {}}])
    assert scheduler.weights.coverage > 1.0
