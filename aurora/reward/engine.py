"""Reward engine coordinating metrics, calculator, and experience logging."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

from .collectors import MetricCollector
from .calculator import RewardCalculator, RewardInputs
from .adaptive import AdaptiveScheduler
from .experience import ExperienceLogger, ExperienceRecord
from .policy import RewardPolicy


@dataclass(slots=True)
class RewardResult:
    reward: float
    metrics: dict
    success: bool
    reasons: list[str]


class RewardEngine:
    def __init__(
        self,
        collector: MetricCollector,
        calculator: RewardCalculator,
        scheduler: AdaptiveScheduler,
        experience_logger: ExperienceLogger,
        log_path: Path,
        policy: RewardPolicy,
    ) -> None:
        self._collector = collector
        self._calculator = calculator
        self._scheduler = scheduler
        self._experience_logger = experience_logger
        self._history_path = log_path
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        self._policy = policy

    def compute_reward(self, ci_results: List[dict]) -> RewardResult:
        snapshot = self._collector.from_ci_results(ci_results)
        inputs = RewardInputs(
            delta_tests_passed=snapshot.tests_passed,
            delta_coverage=snapshot.coverage_delta,
            delta_perf_latency=snapshot.perf_delta,
            delta_security_score=snapshot.security_score,
            delta_cyclomatic=snapshot.complexity_delta,
            policy_bonus=snapshot.policy_bonus,
            bias_penalty=max(snapshot.bias_score - 0.05, 0) * 10,
        )
        reward = self._calculator.compute(inputs)
        metrics_dict = asdict(snapshot)
        history_record = {"reward": reward, "metrics": metrics_dict}
        self._append_history(history_record)
        self._scheduler.adjust([history_record])
        policy_result = self._policy.evaluate(reward, metrics_dict)
        success = policy_result.accepted
        self._experience_logger.append(
            ExperienceRecord(
                context={"task": ci_results},
                edit=metrics_dict,
                telemetry={"policy": policy_result.reasons},
                reward=reward,
                regret=not success,
            )
        )
        return RewardResult(reward=reward, metrics=metrics_dict, success=success, reasons=policy_result.reasons)

    def _append_history(self, record: dict) -> None:
        with self._history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

