"""Reward metric collectors for CI results and telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(slots=True)
class MetricSnapshot:
    tests_passed: float
    coverage_delta: float
    perf_delta: float
    security_score: float
    complexity_delta: float
    policy_bonus: float


class MetricCollector:
    def __init__(self) -> None:
        self._history: list[MetricSnapshot] = []

    def record(self, snapshot: MetricSnapshot) -> None:
        self._history.append(snapshot)

    def last(self) -> MetricSnapshot | None:
        if not self._history:
            return None
        return self._history[-1]

    def history(self) -> Iterable[MetricSnapshot]:
        return tuple(self._history)

