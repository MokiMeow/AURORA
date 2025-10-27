"""Load evaluation configuration from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import EvaluationConfig, SuiteConfig


def load_evaluation_config(path: Path) -> EvaluationConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    suites = {}
    for name, suite_data in data.items():
        suites[name] = SuiteConfig(
            name=name,
            command=suite_data["command"],
            dataset_path=Path(suite_data["dataset"]),
            artifacts_dir=Path(suite_data.get("artifacts", "artifacts/eval")) / name,
        )
    return EvaluationConfig(suites=suites)

