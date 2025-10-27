"""Load evaluation configuration from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import EvaluationConfig, SuiteConfig


def load_evaluation_config(path: Path) -> EvaluationConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    defaults = data.get("defaults", {})
    suites_cfg = data.get("suites", {})
    suites: dict[str, SuiteConfig] = {}
    for name, suite_data in suites_cfg.items():
        merged = {**defaults, **suite_data}
        suites[name] = SuiteConfig(
            name=name,
            command=merged["command"],
            dataset_path=Path(merged["dataset"]),
            artifacts_dir=Path(merged.get("artifacts", "artifacts/eval")) / name,
            schedule=merged.get("schedule", "manual"),
            profile=merged.get("profile", "balanced"),
            timeout_minutes=merged.get("timeout_minutes", 120),
        )
    return EvaluationConfig(
        suites=suites,
        results_dir=Path(data.get("results_dir", "eval/results")),
    )

