"""Reward service wiring configuration-driven engine instances."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from .adaptive import AdaptiveScheduler
from .calculator import RewardCalculator
from .collectors import MetricCollector
from .config import RewardConfig
from .config_loader import load_reward_config
from .engine import RewardEngine, RewardResult
from .experience import ExperienceLogger
from .policy import RewardPolicy
from .reporting import RewardReportWriter
from ..telemetry.errors import ErrorLogger
from ..telemetry.metrics import MetricsEmitter


class RewardService:
    def __init__(
        self,
        config: RewardConfig,
        engine: RewardEngine,
        reporter: RewardReportWriter,
    ) -> None:
        self._config = config
        self._engine = engine
        self._reporter = reporter

    @classmethod
    def from_config(
        cls,
        config_path: Path,
        root: Path | None = None,
        metrics_emitter: MetricsEmitter | None = None,
        error_logger: ErrorLogger | None = None,
    ) -> "RewardService":
        root = root or config_path.parent
        config = load_reward_config(root, config_path)

        reporter = RewardReportWriter(
            store_path=config.explainability.store_path,
            formats=config.explainability.formats,
            keep_last=config.explainability.keep_last,
            enable_timeline=config.explainability.enable_timeline,
            html_template=config.explainability.html_template,
            history_filename=config.explainability.history_filename,
            trend_filename=config.explainability.trend_filename,
        )
        collector = MetricCollector(history_window=config.scheduler.window_runs)
        scheduler = AdaptiveScheduler(
            config.adaptive_weights,
            min_weight=config.scheduler.min_weight,
            max_weight=config.scheduler.max_weight,
            strategy=config.scheduler.strategy,
            history_window=config.scheduler.window_runs,
            adjust_on=config.scheduler.adjust_on,
            explore_probability=config.scheduler.explore_probability,
            reward_floor=config.scheduler.reward_floor,
        )
        calculator = RewardCalculator(config.weights, reporter=reporter)
        experience_logger = ExperienceLogger(
            log_path=config.experience_vault.log_path,
            index_root=config.experience_vault.index_root,
            max_records=config.experience_vault.max_records,
            retention_days=config.experience_vault.retention_days,
            dedupe_fields=config.experience_vault.dedupe_fields,
            redact_fields=config.experience_vault.redact_fields,
            compress=config.experience_vault.compress,
        )
        policy = RewardPolicy(
            min_reward=config.acceptance.min_reward,
            require_security_pass=config.acceptance.require_security_pass,
            max_bias=config.acceptance.max_bias,
            enforce_explainability=config.acceptance.enforce_explainability,
        )
        engine = RewardEngine(
            collector=collector,
            calculator=calculator,
            scheduler=scheduler,
            experience_logger=experience_logger,
            history_path=config.explainability.store_path / config.explainability.history_filename,
            policy=policy,
            metrics_emitter=metrics_emitter or MetricsEmitter(started=True),
            error_logger=error_logger or ErrorLogger(Path("telemetry/errors.jsonl")),
            reporter=reporter,
            bias_penalty=config.bias_penalty,
            regression=config.regression,
        )
        return cls(config=config, engine=engine, reporter=reporter)

    @property
    def config(self) -> RewardConfig:
        return self._config

    def evaluate(self, ci_results: List[dict[str, Any]]) -> RewardResult:
        return self._engine.compute_reward(ci_results)

    def evaluate_from_file(self, path: Path) -> RewardResult:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            ci_results: List[dict[str, Any]] = payload.get("results") or []
        else:
            ci_results = payload
        if not isinstance(ci_results, list):
            raise ValueError("CI results payload must be a list of dictionaries")
        return self.evaluate(ci_results)

    def history(self, limit: int = 20) -> List[dict[str, Any]]:
        return self._engine.api.history(limit=limit)

    def summary(self, limit: int = 50) -> dict[str, Any]:
        return self._engine.api.summary(limit=limit)

    def latest(self) -> dict[str, Any] | None:
        return self._engine.api.latest()

    def run_regression_suite(self) -> List[dict[str, Any]]:
        return self._engine.run_regression_suite()

    def render_explainability(self) -> Path:
        """Return path of latest explainability artifact (JSON)."""
        return self._config.explainability.store_path / "latest_reward.json"


__all__ = ["RewardService"]
