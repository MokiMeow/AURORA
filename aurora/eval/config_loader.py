"""Load evaluation configuration from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import AnalyticsConfig, DatasetManagerConfig, EvaluationConfig, SuiteConfig


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
            scenarios=merged.get("scenarios"),
            baseline_metrics=Path(merged["baseline_metrics"]) if merged.get("baseline_metrics") else None,
            compare_against=merged.get("compare_against"),
            postprocessors=tuple(merged.get("postprocessors", ())),
        )
    dataset_section = data.get("dataset_manager", {})
    dataset_manager = DatasetManagerConfig(
        cache_dir=Path(dataset_section.get("cache_dir", "datasets/cache")),
        manifest_path=Path(dataset_section.get("manifest_path", "datasets/manifest.json")),
        auto_update=dataset_section.get("auto_update", True),
        ttl_hours=int(dataset_section.get("ttl_hours", 24)),
        download_base_url=dataset_section.get("download_base_url"),
    )
    analytics_section = data.get("analytics", {})
    analytics = AnalyticsConfig(
        metrics_csv=Path(analytics_section.get("metrics_csv", "eval/results/metrics.csv")),
        dashboard_html=Path(analytics_section.get("dashboard_html", "docs/reports/weekly_dashboard.html")),
        compare_dir=Path(analytics_section.get("compare_dir", "eval/results/compare")),
    )
    return EvaluationConfig(
        suites=suites,
        results_dir=Path(data.get("results_dir", "eval/results")),
        dataset_manager=dataset_manager,
        analytics=analytics,
    )

