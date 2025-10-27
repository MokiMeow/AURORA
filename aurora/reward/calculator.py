"""Reward calculation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import json


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
    def __init__(self, weights: RewardWeights, explainability_dir: Path | None = None) -> None:
        self._weights = weights
        self._explainability_dir = explainability_dir
        if self._explainability_dir:
            self._explainability_dir.mkdir(parents=True, exist_ok=True)

    def compute(self, inputs: RewardInputs) -> float:
        reward = (
            self._weights.tests * inputs.delta_tests_passed
            + self._weights.coverage * inputs.delta_coverage
            + self._weights.perf * inputs.delta_perf_latency
            + self._weights.security * inputs.delta_security_score
            + self._weights.complexity * inputs.delta_cyclomatic
            + self._weights.policy * inputs.policy_bonus
        )
        if self._explainability_dir:
            self._write_explainability(inputs, reward)
        return reward

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

    def _write_explainability(self, inputs: RewardInputs, reward: float) -> None:
        if not self._explainability_dir:
            return
        path = self._explainability_dir / "latest_reward.json"
        payload = {
            "reward": reward,
            "components": {
                "tests": self._weights.tests * inputs.delta_tests_passed,
                "coverage": self._weights.coverage * inputs.delta_coverage,
                "perf": self._weights.perf * inputs.delta_perf_latency,
                "security": self._weights.security * inputs.delta_security_score,
                "complexity": self._weights.complexity * inputs.delta_cyclomatic,
                "policy": self._weights.policy * inputs.policy_bonus,
            },
        }
        path.write_text(json.dumps(payload, indent=2))

