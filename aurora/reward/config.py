"""Configuration models for the reward engine and experience vault."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Tuple

from .adaptive import AdaptiveWeights
from .calculator import RewardWeights

AdaptiveStrategy = Literal["windowed", "ucb1", "epsilon_greedy"]


@dataclass(slots=True)
class AdaptiveSchedulerConfig:
    window_runs: int
    min_weight: float
    max_weight: float
    adjust_on: Tuple[str, ...]
    strategy: AdaptiveStrategy
    explore_probability: float
    reward_floor: float


@dataclass(slots=True)
class BiasPenaltyConfig:
    enabled: bool
    max_delta: float
    penalty_weight: float


@dataclass(slots=True)
class ExplainabilityConfig:
    store_path: Path
    formats: Tuple[str, ...]
    keep_last: int
    enable_timeline: bool
    html_template: Path | None
    history_filename: str
    trend_filename: str


@dataclass(slots=True)
class AcceptanceConfig:
    min_reward: float
    require_security_pass: bool
    max_bias: float
    enforce_explainability: bool


@dataclass(slots=True)
class ExperienceVaultConfig:
    log_path: Path
    index_root: Path
    max_records: int
    retention_days: int
    dedupe_fields: Tuple[str, ...]
    redact_fields: Tuple[str, ...]
    compress: bool


@dataclass(slots=True)
class RegressionSuiteConfig:
    enabled: bool
    fixtures_path: Path
    tolerance: float


@dataclass(slots=True)
class RewardConfig:
    weights: RewardWeights
    adaptive_weights: AdaptiveWeights
    scheduler: AdaptiveSchedulerConfig
    bias_penalty: BiasPenaltyConfig
    explainability: ExplainabilityConfig
    acceptance: AcceptanceConfig
    experience_vault: ExperienceVaultConfig
    regression: RegressionSuiteConfig


__all__ = [
    "AdaptiveSchedulerConfig",
    "AdaptiveStrategy",
    "BiasPenaltyConfig",
    "ExplainabilityConfig",
    "AcceptanceConfig",
    "ExperienceVaultConfig",
    "RegressionSuiteConfig",
    "RewardConfig",
]
