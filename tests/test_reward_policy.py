"""Tests for reward acceptance policy."""

from aurora.reward.policy import RewardPolicy


def test_reward_policy_accepts_when_threshold_met():
    policy = RewardPolicy(min_reward=0.0, require_security_pass=True)
    result = policy.evaluate(1.0, {"security_score": 1.0})
    assert result.accepted is True


def test_reward_policy_rejects_security_failure():
    policy = RewardPolicy(min_reward=0.0, require_security_pass=True)
    result = policy.evaluate(1.0, {"security_score": 0.5})
    assert result.accepted is False
    assert "Security score" in result.reasons[0]


def test_reward_policy_requires_explainability():
    policy = RewardPolicy(min_reward=0.0, require_security_pass=False, enforce_explainability=True)
    result = policy.evaluate(1.0, {"security_score": 1.0}, explainability_emitted=False)
    assert result.accepted is False
    assert "Explainability" in result.reasons[-1]

