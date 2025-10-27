"""Reward engine coordinating metrics, calculator, and experience logging."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .collectors import MetricCollector
from .calculator import RewardCalculator, RewardInputs
from .adaptive import AdaptiveScheduler
from .experience import ExperienceLogger, ExperienceRecord
from dataclasses import asdict


class RewardEngine:
    def __init__(
        self,
        collector: MetricCollector,
        calculator: RewardCalculator,
        scheduler: AdaptiveScheduler,
        experience_logger: ExperienceLogger,
        log_path: Path,
    ) -> None:
        self._collector = collector
        self._calculator = calculator
        self._scheduler = scheduler
        self._experience_logger = experience_logger
        self._history_path = log_path
        self._history_path.parent.mkdir(parents=True, exist_ok=True)

    def compute_reward(self, ci_results: List[dict]) -> float:
        snapshot = self._collector.from_ci_results(ci_results)
        inputs = RewardInputs(
            delta_tests_passed=snapshot.tests_passed,
            delta_coverage=snapshot.coverage_delta,
            delta_perf_latency=snapshot.perf_delta,
            delta_security_score=snapshot.security_score,
            delta_cyclomatic=snapshot.complexity_delta,
            policy_bonus=snapshot.policy_bonus,
        )
        reward = self._calculator.compute(inputs)
        metrics_dict = asdict(snapshot)
        history_record = {"reward": reward, "metrics": metrics_dict}
        self._append_history(history_record)
        self._scheduler.adjust([history_record])
        success = reward > 0 and snapshot.security_score == 1.0
        self._experience_logger.append(
            ExperienceRecord(
                path="latest",
                reward=reward,
                success=success,
                metadata=metrics_dict,
            )
        )
        return reward

    def _append_history(self, record: dict) -> None:
        with self._history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

