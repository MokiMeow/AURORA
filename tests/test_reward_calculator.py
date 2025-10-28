"""Tests for reward calculator explainability."""

import json
from pathlib import Path

from aurora.reward import RewardCalculator, RewardInputs, RewardWeights


def test_reward_calculator_explainability(tmp_path: Path):
    explain_dir = tmp_path / "explain"
    calculator = RewardCalculator(RewardWeights(1, 1, 1, 1, 1, 1), explainability_dir=explain_dir)
    inputs = RewardInputs(
        delta_tests_passed=1,
        delta_coverage=0,
        delta_perf_latency=0,
        delta_security_score=0,
        delta_cyclomatic=0,
        policy_bonus=0,
    )
    reward = calculator.compute(inputs)
    assert reward == 1
    explain_file = explain_dir / "latest_reward.json"
    assert explain_file.exists()
    data = json.loads(explain_file.read_text(encoding="utf-8"))
    assert data["components"]["tests"] == 1
    assert data["penalties"] == {}

