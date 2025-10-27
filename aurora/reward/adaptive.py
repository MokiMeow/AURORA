"""Adaptive weighting strategy for reward components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class AdaptiveWeights:
    tests: float
    coverage: float
    perf: float
    security: float
    complexity: float
    policy: float


class AdaptiveScheduler:
    def __init__(self, weights: AdaptiveWeights, min_weight: float = 0.1, max_weight: float = 2.5) -> None:
        self._weights = weights
        self._min = min_weight
        self._max = max_weight

    def adjust(self, history: List[dict]) -> AdaptiveWeights:
        failures = sum(1 for record in history if record.get("reward", 0) <= 0)
        if failures > len(history) // 2:
            self._weights.tests = min(self._weights.tests + 0.1, self._max)
            self._weights.coverage = min(self._weights.coverage + 0.1, self._max)
        else:
            self._weights.perf = max(self._weights.perf - 0.1, self._min)
        return self._weights

    @property
    def weights(self) -> AdaptiveWeights:
        return self._weights

