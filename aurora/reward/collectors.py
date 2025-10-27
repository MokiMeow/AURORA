"""Reward metric collectors for CI results and telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Dict


@dataclass(slots=True)
class MetricSnapshot:
    tests_passed: float
    coverage_delta: float
    perf_delta: float
    security_score: float
    complexity_delta: float
    policy_bonus: float
    bias_score: float = 0.0


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

    def from_ci_results(self, results: List[Dict[str, object]]) -> MetricSnapshot:
        tests_passed = sum(1 for r in results if r["success"] and "test" in r["step"])
        coverage_delta = 0.1 if any("coverage" in r["step"] and r["success"] for r in results) else 0.0
        perf_delta = 0.1 if any("perf" in r["step"] or "k6" in r["step"] for r in results if r["success"]) else 0.0
        security_failures = [r for r in results if not r["success"] and any(keyword in r["step"] for keyword in {"security", "cve", "sbom", "license", "bandit", "semgrep"})]
        security_score = 1.0 if not security_failures else 0.0
        complexity_delta = 0.0
        policy_bonus = 0.1 if all(r["success"] for r in results) else 0.0
        bias_score = 0.0
        if any("bias" in r["step"] for r in results):
            bias_score = 0.06
        snapshot = MetricSnapshot(
            tests_passed=float(tests_passed),
            coverage_delta=coverage_delta,
            perf_delta=perf_delta,
            security_score=security_score,
            complexity_delta=complexity_delta,
            policy_bonus=policy_bonus,
            bias_score=bias_score,
        )
        self.record(snapshot)
        return snapshot

