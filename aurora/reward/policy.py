"""Reward acceptance policy enforcement."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RewardPolicyResult:
    accepted: bool
    reasons: list[str]


class RewardPolicy:
    def __init__(self, min_reward: float = 0.0, require_security_pass: bool = True) -> None:
        self._min_reward = min_reward
        self._require_security_pass = require_security_pass

    def evaluate(self, reward: float, metrics: dict) -> RewardPolicyResult:
        reasons: list[str] = []
        accepted = True
        if reward < self._min_reward:
            accepted = False
            reasons.append("Reward below minimum threshold")
        if self._require_security_pass and metrics.get("security_score", 0) < 1.0:
            accepted = False
            reasons.append("Security score did not pass")
        return RewardPolicyResult(accepted=accepted, reasons=reasons)

