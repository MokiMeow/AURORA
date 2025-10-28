"""Evaluation configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


@dataclass(slots=True)
class SuiteConfig:
    name: str
    command: list[str]
    dataset_path: Path
    artifacts_dir: Path
    schedule: str
    profile: str
    timeout_minutes: int
    scenarios: Optional[int]
    baseline_metrics: Optional[Path]
    compare_against: Optional[str]
    postprocessors: Tuple[str, ...]


@dataclass(slots=True)
class DatasetManagerConfig:
    cache_dir: Path
    manifest_path: Path
    auto_update: bool
    ttl_hours: int
    download_base_url: Optional[str]


@dataclass(slots=True)
class AnalyticsConfig:
    metrics_csv: Path
    dashboard_html: Path
    compare_dir: Path


@dataclass(slots=True)
class EvaluationConfig:
    suites: Dict[str, SuiteConfig]
    results_dir: Path
    dataset_manager: DatasetManagerConfig
    analytics: AnalyticsConfig

