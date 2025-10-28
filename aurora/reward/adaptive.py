"""Adaptive weighting strategy for reward components."""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, List

from .calculator import RewardWeights


@dataclass(slots=True)
class AdaptiveWeights:
    tests: float
    coverage: float
    perf: float
    security: float
    complexity: float
    policy: float


class AdaptiveScheduler:
    COMPONENTS = ("tests", "coverage", "perf", "security", "complexity", "policy")

    def __init__(
        self,
        weights: AdaptiveWeights,
        min_weight: float = 0.1,
        max_weight: float = 2.5,
        strategy: str = "windowed",
        history_window: int = 20,
        adjust_on: Iterable[str] | None = None,
        explore_probability: float = 0.1,
        reward_floor: float = -1.0,
    ) -> None:
        self._weights = weights
        self._min = min_weight
        self._max = max_weight
        self._strategy = strategy
        self._history: Deque[dict] = deque(maxlen=history_window)
        self._adjust_on = tuple(adjust_on or ())
        self._explore_probability = explore_probability
        self._reward_floor = reward_floor
        self._component_totals: Dict[str, float] = {component: 0.0 for component in self.COMPONENTS}
        self._component_counts: Dict[str, int] = {component: 0 for component in self.COMPONENTS}

    def adjust(self, records: List[dict]) -> AdaptiveWeights:
        for record in records:
            self._history.append(record)
            components = record.get("components", {})
            for component in self.COMPONENTS:
                contribution = float(components.get(component, 0.0))
                if contribution != 0:
                    self._component_totals[component] += contribution
                    self._component_counts[component] += 1

        if not self._history:
            return self._weights

        if self._strategy == "ucb1":
            self._apply_ucb()
        elif self._strategy == "epsilon_greedy":
            self._apply_epsilon()
        else:
            self._apply_windowed()
        return self._weights

    def _apply_windowed(self) -> None:
        failures = sum(1 for record in self._history if record.get("reward", 0.0) <= self._reward_floor)
        if failures / max(len(self._history), 1) >= 0.4:
            self._increase_weight("tests", 0.1)
            self._increase_weight("security", 0.1)

        if "coverage_regressions" in self._adjust_on and any(
            record.get("metrics", {}).get("coverage_delta", 0.0) <= 0.0 for record in self._history
        ):
            self._increase_weight("coverage", 0.05)

        if "security_findings" in self._adjust_on and any(
            record.get("metrics", {}).get("security_findings", 0.0) > 0 for record in self._history
        ):
            self._increase_weight("security", 0.1)

        if "failing_tests" in self._adjust_on and any(
            record.get("metrics", {}).get("tests_failed", 0.0) > 0 for record in self._history
        ):
            self._increase_weight("tests", 0.05)

        if failures == 0 and self._history:
            # reward stability; slowly rebalance towards performance improvements
            self._decrease_weight("tests", 0.05)
            self._increase_weight("perf", 0.05)

    def _apply_ucb(self) -> None:
        candidates = [component for component in self.COMPONENTS if self._component_counts[component] > 0]
        if not candidates:
            self._apply_windowed()
            return
        total = sum(self._component_counts[component] for component in candidates) or 1
        ucb_scores: Dict[str, float] = {}
        for component in candidates:
            count = self._component_counts[component]
            mean = self._component_totals[component] / count if count else 0.0
            bonus = math.sqrt(2 * math.log(total + 1) / (count + 1))
            ucb_scores[component] = mean + bonus

        target = max(ucb_scores, key=ucb_scores.get)
        self._increase_weight(target, 0.05)
        for component in self.COMPONENTS:
            if component != target:
                self._decrease_weight(component, 0.02)

    def _apply_epsilon(self) -> None:
        if random.random() < self._explore_probability:
            component = random.choice(self.COMPONENTS)
            self._increase_weight(component, 0.05)
            return

        # Exploit the component with largest positive contribution
        contributions = {
            component: (
                self._component_totals[component] / self._component_counts[component]
                if self._component_counts[component]
                else 0.0
            )
            for component in self.COMPONENTS
        }
        target = max(contributions, key=contributions.get)
        self._increase_weight(target, 0.05)
        for component in self.COMPONENTS:
            if component != target:
                self._decrease_weight(component, 0.01)

    def _increase_weight(self, component: str, delta: float) -> None:
        current = getattr(self._weights, component)
        setattr(self._weights, component, min(current + delta, self._max))

    def _decrease_weight(self, component: str, delta: float) -> None:
        current = getattr(self._weights, component)
        setattr(self._weights, component, max(current - delta, self._min))

    @property
    def weights(self) -> AdaptiveWeights:
        return self._weights

    def to_reward_weights(self) -> RewardWeights:
        return RewardWeights(
            tests=self._weights.tests,
            coverage=self._weights.coverage,
            perf=self._weights.perf,
            security=self._weights.security,
            complexity=self._weights.complexity,
            policy=self._weights.policy,
        )

