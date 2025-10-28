"""Reward calculation utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .reporting import RewardObservation, RewardReportWriter


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
    bias_penalty: float = 0.0


@dataclass(slots=True)
class RewardComputation:
    reward: float
    components: dict[str, float]
    penalties: dict[str, float]


class RewardCalculator:
    def __init__(
        self,
        weights: RewardWeights,
        explainability_dir: Path | None = None,
        reporter: RewardReportWriter | None = None,
    ) -> None:
        self._weights = weights
        self._explainability_dir = explainability_dir
        self._reporter = reporter
        if self._explainability_dir:
            self._explainability_dir.mkdir(parents=True, exist_ok=True)
            if self._reporter is None:
                self._reporter = RewardReportWriter(self._explainability_dir)

    def compute(self, inputs: RewardInputs) -> float:
        return self.compute_breakdown(inputs, emit=True).reward

    def compute_breakdown(
        self,
        inputs: RewardInputs,
        metadata: dict[str, Any] | None = None,
        emit: bool = False,
    ) -> RewardComputation:
        components = {
            "tests": self._weights.tests * inputs.delta_tests_passed,
            "coverage": self._weights.coverage * inputs.delta_coverage,
            "perf": self._weights.perf * inputs.delta_perf_latency,
            "security": self._weights.security * inputs.delta_security_score,
            "complexity": self._weights.complexity * inputs.delta_cyclomatic,
            "policy": self._weights.policy * inputs.policy_bonus,
        }
        penalties = {"bias": inputs.bias_penalty} if getattr(inputs, "bias_penalty", 0.0) else {}
        reward = sum(components.values()) - sum(penalties.values())
        computation = RewardComputation(reward=reward, components=components, penalties=penalties)

        if emit:
            self._emit_explainability(computation, metadata)
        return computation

    def update_weights(self, weights: RewardWeights) -> None:
        self._weights = weights

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

    def _emit_explainability(
        self, computation: RewardComputation, metadata: dict[str, Any] | None = None
    ) -> None:
        if self._reporter is not None:
            observation = RewardObservation(
                reward=computation.reward,
                components=computation.components,
                penalties=computation.penalties,
                metrics={},
                success=True,
                reasons=[],
                metadata=metadata or {},
            )
            self._reporter.write(observation)
            return

        if not self._explainability_dir:
            return

        path = self._explainability_dir / "latest_reward.json"
        payload = {
            "reward": computation.reward,
            "components": computation.components,
            "penalties": computation.penalties,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

