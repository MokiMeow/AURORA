"""Evaluation configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(slots=True)
class SuiteConfig:
    name: str
    command: list[str]
    dataset_path: Path
    artifacts_dir: Path
    schedule: str
    profile: str
    timeout_minutes: int


@dataclass(slots=True)
class EvaluationConfig:
    suites: Dict[str, SuiteConfig]
    results_dir: Path

