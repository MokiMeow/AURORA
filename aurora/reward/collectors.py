"""Reward metric collectors for CI results and telemetry."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Deque, Iterable


@dataclass(slots=True)
class MetricSnapshot:
    suite: str
    tests_passed: float
    tests_failed: float
    coverage_percent: float
    coverage_delta: float
    perf_p95_ms: float
    perf_delta: float
    security_score: float
    security_findings: float
    complexity_delta: float
    policy_bonus: float
    bias_score: float
    duration_seconds: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


class MetricCollector:
    def __init__(self, history_window: int = 50) -> None:
        self._history: Deque[MetricSnapshot] = deque(maxlen=history_window)

    def record(self, snapshot: MetricSnapshot) -> None:
        self._history.append(snapshot)

    def last(self) -> MetricSnapshot | None:
        if not self._history:
            return None
        return self._history[-1]

    def history(self) -> Iterable[MetricSnapshot]:
        return tuple(self._history)

    def from_ci_results(self, results: list[dict[str, Any]]) -> MetricSnapshot:
        aggregated = {
            "suite": "ci",
            "tests_passed": 0.0,
            "tests_failed": 0.0,
            "coverage_percent": 0.0,
            "coverage_delta": 0.0,
            "perf_p95_ms": 0.0,
            "perf_delta": 0.0,
            "security_score": 1.0,
            "security_findings": 0.0,
            "complexity_delta": 0.0,
            "policy_bonus": 0.0,
            "bias_score": 0.0,
            "duration_seconds": 0.0,
        }

        for result in results:
            suite = result.get("suite") or result.get("pipeline") or result.get("workflow")
            if suite:
                aggregated["suite"] = str(suite)
            metrics = self._resolve_metrics(result)

            tests_metrics = metrics.get("tests", {})
            aggregated["tests_passed"] += float(tests_metrics.get("passed", 0.0))
            aggregated["tests_failed"] += float(tests_metrics.get("failed", 0.0))
            if "total" in tests_metrics and tests_metrics.get("total"):
                aggregated["tests_passed"] = max(
                    aggregated["tests_passed"],
                    float(tests_metrics.get("total", 0.0)) - float(tests_metrics.get("failed", 0.0)),
                )

            coverage_metrics = metrics.get("coverage", {})
            if "percent" in coverage_metrics:
                aggregated["coverage_percent"] = float(coverage_metrics["percent"])
            aggregated["coverage_delta"] += float(coverage_metrics.get("delta", 0.0))

            perf_metrics = metrics.get("performance", {})
            if "p95_ms" in perf_metrics:
                aggregated["perf_p95_ms"] = max(
                    aggregated["perf_p95_ms"], float(perf_metrics["p95_ms"])
                )
            aggregated["perf_delta"] += float(perf_metrics.get("delta_ms", 0.0))

            security_metrics = metrics.get("security", {})
            if "score" in security_metrics:
                aggregated["security_score"] = min(
                    aggregated["security_score"], float(security_metrics["score"])
                )
            aggregated["security_findings"] += float(security_metrics.get("findings", 0.0))

            complexity_metrics = metrics.get("complexity", {})
            aggregated["complexity_delta"] += float(complexity_metrics.get("delta", 0.0))

            policy_metrics = metrics.get("policy", {})
            aggregated["policy_bonus"] += float(policy_metrics.get("bonus", 0.0))

            bias_metrics = metrics.get("bias", {})
            aggregated["bias_score"] = max(
                aggregated["bias_score"], float(bias_metrics.get("score", aggregated["bias_score"]))
            )

            aggregated["duration_seconds"] += float(result.get("duration_seconds", 0.0))

            self._apply_heuristics(aggregated, result, metrics)

        snapshot = MetricSnapshot(**aggregated)
        self.record(snapshot)
        return snapshot

    @staticmethod
    def _resolve_metrics(result: dict[str, Any]) -> dict[str, Any]:
        metrics_obj = result.get("metrics")
        if isinstance(metrics_obj, dict):
            return metrics_obj

        metrics_path = result.get("metrics_path") or result.get("artifact_path")
        if metrics_path:
            path = Path(metrics_path)
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    return {}
        return {}

    @staticmethod
    def _apply_heuristics(
        aggregated: dict[str, float], result: dict[str, Any], metrics: dict[str, Any]
    ) -> None:
        step = str(result.get("step", "")).lower()
        success = bool(result.get("success", False))

        if ("tests" not in metrics) and ("test" in step or "pytest" in step):
            if success:
                aggregated["tests_passed"] += 1.0
            else:
                aggregated["tests_failed"] += 1.0

        if "coverage" not in metrics and "coverage" in step and success:
            aggregated["coverage_delta"] = max(aggregated["coverage_delta"], 0.05)
            if aggregated["coverage_percent"] == 0.0:
                aggregated["coverage_percent"] = 75.0

        if "performance" not in metrics and any(
            keyword in step for keyword in ("perf", "load", "k6")
        ) and success:
            aggregated["perf_delta"] += 0.05
            aggregated["perf_p95_ms"] = max(aggregated["perf_p95_ms"], 500.0)

        if (
            "security" not in metrics
            and any(keyword in step for keyword in ("security", "bandit", "semgrep", "cve"))
            and not success
        ):
            aggregated["security_score"] = 0.0
            aggregated["security_findings"] += 1.0

        if "complexity" not in metrics and "complexity" in step:
            aggregated["complexity_delta"] += -0.02 if success else 0.05

        if "bias" not in metrics and "bias" in step:
            aggregated["bias_score"] = max(aggregated["bias_score"], 0.06)

        if "policy" not in metrics and success and result.get("policy_bonus"):
            aggregated["policy_bonus"] += float(result["policy_bonus"])

