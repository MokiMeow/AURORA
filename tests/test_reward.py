"""Tests for the reward calculator."""

from aurora.reward import RewardCalculator, RewardInputs


def test_reward_calculation():
    calculator = RewardCalculator.from_mapping(
        {
            "tests": 1.0,
            "coverage": 0.5,
            "perf": 0.4,
            "security": 1.5,
            "complexity": -0.3,
            "policy": 0.8,
        }
    )
    inputs = RewardInputs(
        delta_tests_passed=2,
        delta_coverage=0.1,
        delta_perf_latency=0.05,
        delta_security_score=1.0,
        delta_cyclomatic=-0.2,
        policy_bonus=0.5,
    )
    reward = calculator.compute(inputs)

    expected = (
        1.0 * inputs.delta_tests_passed
        + 0.5 * inputs.delta_coverage
        + 0.4 * inputs.delta_perf_latency
        + 1.5 * inputs.delta_security_score
        + (-0.3) * inputs.delta_cyclomatic
        + 0.8 * inputs.policy_bonus
    )
    assert reward == expected