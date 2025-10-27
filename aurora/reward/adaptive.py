"""Adaptive weighting strategy for reward components."""

from __future__ import annotations

from dataclasses import dataclass


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

    def adjust(self, history: list[dict]) -> AdaptiveWeights:
        # Placeholder logic: real implementation would analyze history
        return self._weights

    @property
    def weights(self) -> AdaptiveWeights:
        return self._weights

