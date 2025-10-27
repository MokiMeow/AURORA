"""Tests for executor policy evaluator."""

from aurora.executor.policy import PolicyEvaluator


def test_policy_accepts_success():
    evaluator = PolicyEvaluator(policy_path=None)
    result = evaluator.evaluate([
        {"step": "lint", "success": True, "log": "lint.log"},
        {"step": "test", "success": True, "log": "test.log"},
    ])
    assert result.accepted is True


def test_policy_rejects_failure():
    evaluator = PolicyEvaluator(policy_path=None)
    result = evaluator.evaluate([
        {"step": "lint", "success": False, "log": "lint.log"},
    ])
    assert result.accepted is False
    assert "CI step failed" in result.reasons[0]

