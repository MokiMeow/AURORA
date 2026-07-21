"""Reward engine coordinating metrics, calculator, and experience logging."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

from .adaptive import AdaptiveScheduler
from .api import RewardAPI
from .calculator import RewardCalculator, RewardInputs
from .collectors import MetricCollector
from .config import BiasPenaltyConfig, RegressionSuiteConfig
from .experience import ExperienceLogger, ExperienceRecord
from .policy import RewardPolicy
from .reporting import RewardObservation, RewardReportWriter
from ..telemetry.errors import ErrorLogger
from ..telemetry.metrics import MetricsEmitter
from ..telemetry.pdca import PDCAEntry


@dataclass(slots=True)
class RewardResult:
    timestamp: str
    reward: float
    metrics: dict[str, Any]
    success: bool
    reasons: list[str]
    components: dict[str, float]
    penalties: dict[str, float]


class RewardEngine:
    def __init__(
        self,
        collector: MetricCollector,
        calculator: RewardCalculator,
        scheduler: AdaptiveScheduler,
        experience_logger: ExperienceLogger,
        history_path: Path,
        policy: RewardPolicy,
        metrics_emitter: MetricsEmitter | None = None,
        error_logger: ErrorLogger | None = None,
        reporter: RewardReportWriter | None = None,
        bias_penalty: BiasPenaltyConfig | None = None,
        regression: RegressionSuiteConfig | None = None,
    ) -> None:
        self._collector = collector
        self._calculator = calculator
        self._scheduler = scheduler
        self._experience_logger = experience_logger
        self._history_path = history_path
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        self._policy = policy
        self._metrics = metrics_emitter or MetricsEmitter()
        self._errors = error_logger or ErrorLogger(Path("telemetry/errors.jsonl"))
        self._reporter = reporter
        self._bias_penalty = bias_penalty
        self._regression = regression
        self._api = RewardAPI(self._history_path)

    def compute_reward(self, ci_results: List[dict[str, Any]]) -> RewardResult:
        timestamp = datetime.now(timezone.utc).isoformat()
        snapshot = self._collector.from_ci_results(ci_results)
        bias_penalty_value = self._compute_bias_penalty(snapshot.bias_score)
        inputs = RewardInputs(
            delta_tests_passed=snapshot.tests_passed - snapshot.tests_failed,
            delta_coverage=snapshot.coverage_delta,
            delta_perf_latency=snapshot.perf_delta,
            delta_security_score=snapshot.security_score,
            delta_cyclomatic=snapshot.complexity_delta,
            policy_bonus=snapshot.policy_bonus,
            bias_penalty=bias_penalty_value,
        )

        breakdown = self._calculator.compute_breakdown(inputs, metadata={"timestamp": timestamp}, emit=False)
        reward = breakdown.reward
        metrics_dict = snapshot.as_dict()
        schedule_record = {
            "reward": reward,
            "components": breakdown.components,
            "metrics": metrics_dict,
        }
        self._scheduler.adjust([schedule_record])
        self._calculator.update_weights(self._scheduler.to_reward_weights())

        explainability_emitted = self._reporter is not None
        policy_result = self._policy.evaluate(
            reward,
            metrics_dict,
            explainability_emitted=explainability_emitted,
        )
        success = policy_result.accepted

        history_record = {
            "timestamp": timestamp,
            "reward": reward,
            "components": breakdown.components,
            "penalties": breakdown.penalties,
            "metrics": metrics_dict,
            "success": success,
            "reasons": policy_result.reasons,
        }
        self._append_history(history_record)

        observation_metadata = self._build_metadata(ci_results, snapshot, bias_penalty_value)
        observation = RewardObservation(
            reward=reward,
            components=breakdown.components,
            penalties=breakdown.penalties,
            metrics=metrics_dict,
            success=success,
            reasons=policy_result.reasons,
            metadata=observation_metadata,
        )
        if self._reporter:
            self._reporter.write(observation)

        self._log_experience(observation, ci_results)
        self._metrics.record_reward(str(metrics_dict.get("suite", "ci")), reward)
        PDCAEntry(
            phase="Check",
            event="reward_calculated",
            payload={
                "timestamp": timestamp,
                "reward": reward,
                "success": success,
                "metrics": metrics_dict,
                "reasons": policy_result.reasons,
            },
        )
        return RewardResult(
            timestamp=timestamp,
            reward=reward,
            metrics=metrics_dict,
            success=success,
            reasons=policy_result.reasons,
            components=breakdown.components,
            penalties=breakdown.penalties,
        )

    @property
    def api(self) -> RewardAPI:
        return self._api

    def run_regression_suite(self) -> list[dict[str, Any]]:
        if not self._regression or not self._regression.enabled:
            return []
        fixture_path = self._regression.fixtures_path
        if not fixture_path.exists():
            self._errors.log(
                "reward_regression",
                "Regression fixture path missing",
                {"path": str(fixture_path)},
            )
            return []

        mismatches: list[dict[str, Any]] = []
        for fixture_file in fixture_path.glob("*.json"):
            try:
                fixture = json.loads(fixture_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._errors.log(
                    "reward_regression",
                    "Invalid regression fixture",
                    {"path": str(fixture_file)},
                )
                continue
            expected = fixture.get("expected_reward")
            ci_results = fixture.get("ci_results", [])
            actual_result = self.compute_reward(ci_results)
            if expected is None:
                continue
            delta = abs(actual_result.reward - expected)
            if delta > self._regression.tolerance:
                mismatches.append(
                    {
                        "fixture": str(fixture_file),
                        "expected": expected,
                        "actual": actual_result.reward,
                        "delta": delta,
                    }
                )
        return mismatches

    def _build_metadata(self, ci_results: List[dict[str, Any]], snapshot: Any, bias_penalty: float) -> dict[str, Any]:
        task_id = self._extract_field(ci_results, ("task_id", "task"))
        diff_hash = self._extract_field(ci_results, ("diff_hash", "change_id", "patch_hash"))
        policy_reasons = []
        for result in ci_results:
            policy_reasons.extend(result.get("policy_reasons", []))
        return {
            "task": task_id or snapshot.suite,
            "task_id": task_id or snapshot.suite,
            "diff_hash": diff_hash or "",
            "suite": snapshot.suite,
            "tests_failed": snapshot.tests_failed,
            "bias_penalty": bias_penalty,
            "policy_reasons": policy_reasons,
        }

    def _log_experience(self, observation: RewardObservation, ci_results: List[dict[str, Any]]) -> None:
        context = {"task": observation.metadata.get("task"), "suite": observation.metrics.get("suite")}
        edit_summary = {
            "components": observation.components,
            "penalties": observation.penalties,
            "ci_steps": [result.get("step") for result in ci_results],
        }
        telemetry = {
            "policy": observation.reasons,
            "success": observation.success,
        }
        self._experience_logger.append(
            ExperienceRecord(
                context=context,
                edit=edit_summary,
                telemetry=telemetry,
                reward=observation.reward,
                regret=not observation.success,
                metadata=observation.metadata,
            )
        )

    def _append_history(self, record: dict[str, Any]) -> None:
        with self._history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def _compute_bias_penalty(self, bias_score: float) -> float:
        if not self._bias_penalty or not self._bias_penalty.enabled:
            return max(bias_score - 0.05, 0.0) * 10
        delta = max(bias_score - self._bias_penalty.max_delta, 0.0)
        return delta * self._bias_penalty.penalty_weight

    @staticmethod
    def _extract_field(results: List[dict[str, Any]], keys: tuple[str, ...]) -> str | None:
        for result in results:
            for key in keys:
                value = result.get(key)
                if value:
                    return str(value)
        return None


__all__ = ["RewardEngine", "RewardResult"]
