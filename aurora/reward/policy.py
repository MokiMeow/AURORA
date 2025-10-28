"""Reward acceptance policy enforcement."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RewardPolicyResult:
    accepted: bool
    reasons: list[str]


class RewardPolicy:
    def __init__(
        self,
        min_reward: float = 0.0,
        require_security_pass: bool = True,
        max_bias: float = 0.05,
        enforce_explainability: bool = False,
    ) -> None:
        self._min_reward = min_reward
        self._require_security_pass = require_security_pass
        self._max_bias = max_bias
        self._enforce_explainability = enforce_explainability

    def evaluate(
        self,
        reward: float,
        metrics: dict,
        explainability_emitted: bool = True,
    ) -> RewardPolicyResult:
        reasons: list[str] = []
        accepted = True
        if reward < self._min_reward:
            accepted = False
            reasons.append("Reward below minimum threshold")
        if self._require_security_pass and metrics.get("security_score", 0.0) < 1.0:
            accepted = False
            reasons.append("Security score did not pass")
        if metrics.get("security_findings", 0.0) > 0:
            accepted = False
            reasons.append("Outstanding security findings present")
        if metrics.get("bias_score", 0.0) > self._max_bias:
            accepted = False
            reasons.append("Bias score exceeded threshold")
        if metrics.get("coverage_delta", 0.0) < 0:
            reasons.append("Coverage regression detected")
        if self._enforce_explainability and not explainability_emitted:
            accepted = False
            reasons.append("Explainability artifact missing")
        return RewardPolicyResult(accepted=accepted, reasons=reasons)

