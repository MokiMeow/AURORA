"""Tests for executor policy evaluator."""

from aurora.executor.policy import PolicyEvaluator


def test_policy_accepts_success():
    evaluator = PolicyEvaluator(policy_path=None)
    result = evaluator.evaluate([
        {"step": "lint", "success": True, "log": "lint.log"},
        {"step": "test", "success": True, "log": "test.log"},
    ])
    assert result.accepted is True


def test_policy_rejects_security_failure():
    evaluator = PolicyEvaluator(policy_path=None)
    result = evaluator.evaluate([
        {"step": "lint", "success": False, "log": "lint.log"},
    ])
    assert result.accepted is False
    assert "CI step failed" in result.reasons[0]


def test_policy_requires_specific_steps(tmp_path):
    policy_file = tmp_path / "policy.json"
    policy_file.write_text('{"required_steps": ["k6"]}')
    evaluator = PolicyEvaluator(policy_path=policy_file)
    result = evaluator.evaluate([
        {"step": "lint", "success": True, "log": "lint.log"},
    ])
    assert result.accepted is False
    assert any("Required step" in reason for reason in result.reasons)

