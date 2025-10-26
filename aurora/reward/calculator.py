"""Reward calculation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(slots=True)
class RewardWeights:
    tests: float
    coverage: float
    perf: float
    security: float
    complexity: float
    policy: float


@dataclass(slots=True)
class RewardInputs:
    delta_tests_passed: float
    delta_coverage: float
    delta_perf_latency: float
    delta_security_score: float
    delta_cyclomatic: float
    policy_bonus: float


class RewardCalculator:
    def __init__(self, weights: RewardWeights) -> None:
        self._weights = weights

    def compute(self, inputs: RewardInputs) -> float:
        return (
            self._weights.tests * inputs.delta_tests_passed
            + self._weights.coverage * inputs.delta_coverage
            + self._weights.perf * inputs.delta_perf_latency
            + self._weights.security * inputs.delta_security_score
            + self._weights.complexity * inputs.delta_cyclomatic
            + self._weights.policy * inputs.policy_bonus
        )

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, float]) -> "RewardCalculator":
        weights = RewardWeights(
            tests=mapping.get("tests", 0.0),
            coverage=mapping.get("coverage", 0.0),
            perf=mapping.get("perf", 0.0),
            security=mapping.get("security", 0.0),
            complexity=mapping.get("complexity", 0.0),
            policy=mapping.get("policy", 0.0),
        )
        return cls(weights)

