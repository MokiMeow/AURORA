"""Load reward configuration from YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import yaml

from .adaptive import AdaptiveWeights
from .calculator import RewardWeights
from .config import (
    AcceptanceConfig,
    AdaptiveSchedulerConfig,
    BiasPenaltyConfig,
    ExplainabilityConfig,
    ExperienceVaultConfig,
    RegressionSuiteConfig,
    RewardConfig,
)

DEFAULT_STRATEGY = "windowed"
ALLOWED_STRATEGIES = {"windowed", "ucb1", "epsilon_greedy"}


def _ensure_sequence(values: Sequence[str] | str | None) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        return (values,)
    return tuple(str(v) for v in values)


def load_reward_config(root: Path, path: Path) -> RewardConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    weights_section = data.get("weights", {})
    weights = RewardWeights(
        tests=float(weights_section.get("tests", 1.0)),
        coverage=float(weights_section.get("coverage", 0.5)),
        perf=float(weights_section.get("perf", 0.4)),
        security=float(weights_section.get("security", 1.5)),
        complexity=float(weights_section.get("complexity", -0.3)),
        policy=float(weights_section.get("policy", 0.8)),
    )

    scheduler_section = data.get("adaptive_scheduler", {})
    initial_weights_section = scheduler_section.get("initial_weights", weights_section)
    adaptive_weights = AdaptiveWeights(
        tests=float(initial_weights_section.get("tests", weights.tests)),
        coverage=float(initial_weights_section.get("coverage", weights.coverage)),
        perf=float(initial_weights_section.get("perf", weights.perf)),
        security=float(initial_weights_section.get("security", weights.security)),
        complexity=float(initial_weights_section.get("complexity", weights.complexity)),
        policy=float(initial_weights_section.get("policy", weights.policy)),
    )
    strategy = str(scheduler_section.get("strategy", DEFAULT_STRATEGY))
    if strategy not in ALLOWED_STRATEGIES:
        raise ValueError(f"Unsupported adaptive scheduler strategy '{strategy}'")
    adjust_on = scheduler_section.get("adjust_on", ())
    if isinstance(adjust_on, dict):
        adjust_keys: Iterable[str] = adjust_on.keys()
    else:
        adjust_keys = adjust_on
    scheduler = AdaptiveSchedulerConfig(
        window_runs=int(scheduler_section.get("window_runs", 20)),
        min_weight=float(scheduler_section.get("min_weight", 0.1)),
        max_weight=float(scheduler_section.get("max_weight", 2.5)),
        adjust_on=_ensure_sequence(tuple(adjust_keys)),
        strategy=strategy,  # type: ignore[arg-type]
        explore_probability=float(scheduler_section.get("explore_probability", 0.1)),
        reward_floor=float(scheduler_section.get("reward_floor", -1.0)),
    )

    bias_section = data.get("bias_penalty", {})
    bias_penalty = BiasPenaltyConfig(
        enabled=bool(bias_section.get("enabled", True)),
        max_delta=float(bias_section.get("max_delta", 0.05)),
        penalty_weight=float(bias_section.get("penalty_weight", 2.0)),
    )

    explain_section = data.get("explainability", {})
    store_path = root / explain_section.get("store_path", "artifacts/reward_reports")
    formats = explain_section.get("formats")
    if not formats:
        single_format = explain_section.get("format", "json")
        formats = [single_format]
    explainability = ExplainabilityConfig(
        store_path=store_path,
        formats=_ensure_sequence(formats),
        keep_last=int(explain_section.get("keep_last", 50)),
        enable_timeline=bool(explain_section.get("enable_timeline", True)),
        html_template=(
            root / explain_section["html_template"]
            if explain_section.get("html_template")
            else None
        ),
        history_filename=explain_section.get("history_filename", "reward_history.jsonl"),
        trend_filename=explain_section.get("trend_filename", "reward_trend.html"),
    )

    acceptance_section = data.get("acceptance", {})
    acceptance = AcceptanceConfig(
        min_reward=float(acceptance_section.get("min_reward", 0.0)),
        require_security_pass=bool(acceptance_section.get("require_security_pass", True)),
        max_bias=float(acceptance_section.get("max_bias", 0.05)),
        enforce_explainability=bool(acceptance_section.get("enforce_explainability", True)),
    )

    experience_section = data.get("experience_vault", {})
    experience = ExperienceVaultConfig(
        log_path=root / experience_section.get("log_path", "experience/reward.log.jsonl"),
        index_root=root / experience_section.get("index_root", "experience/indices"),
        max_records=int(experience_section.get("max_records", 5000)),
        retention_days=int(experience_section.get("retention_days", 180)),
        dedupe_fields=_ensure_sequence(experience_section.get("dedupe_fields", ("task", "diff_hash"))),
        redact_fields=_ensure_sequence(experience_section.get("redact_fields", ())),
        compress=bool(experience_section.get("compress", False)),
    )

    regression_section = data.get("regression_suite", {})
    regression = RegressionSuiteConfig(
        enabled=bool(regression_section.get("enabled", True)),
        fixtures_path=root
        / regression_section.get("fixtures_path", "tests/fixtures/reward_runs"),
        tolerance=float(regression_section.get("tolerance", 0.05)),
    )

    return RewardConfig(
        weights=weights,
        adaptive_weights=adaptive_weights,
        scheduler=scheduler,
        bias_penalty=bias_penalty,
        explainability=explainability,
        acceptance=acceptance,
        experience_vault=experience,
        regression=regression,
    )


__all__ = ["load_reward_config"]
