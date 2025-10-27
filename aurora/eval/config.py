"""Evaluation configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(slots=True)
class SuiteConfig:
    name: str
    command: list[str]
    dataset_path: Path
    artifacts_dir: Path


@dataclass(slots=True)
class EvaluationConfig:
    suites: dict[str, SuiteConfig]

