"""Tests for evaluation service."""

import json
from pathlib import Path

from aurora.eval.config import (
    AnalyticsConfig,
    DatasetManagerConfig,
    EvaluationConfig,
    SuiteConfig,
)
from aurora.eval.service import EvaluationService


class DummyProcess:
    def __init__(self) -> None:
        self.returncode = 0
        self.stdout = "METRIC:success_rate=0.8\nMETRIC:latency=120\nPATCH_CORRECT=3\nCOMPILE_FAILURES=1"
        self.stderr = ""


def test_evaluation_service_runs_and_generates_artifacts(monkeypatch, tmp_path: Path):
    suite = SuiteConfig(
        name="lite",
        command=["python", "run.py"],
        dataset_path=tmp_path / "datasets" / "lite",
        artifacts_dir=tmp_path / "artifacts",
        schedule="nightly",
        profile="balanced",
        timeout_minutes=1,
        scenarios=5,
        baseline_metrics=None,
        compare_against=None,
        postprocessors=("scripts/post/process.py",),
    )
    dataset_manager = DatasetManagerConfig(
        cache_dir=tmp_path / "cache",
        manifest_path=tmp_path / "cache" / "manifest.json",
        auto_update=True,
        ttl_hours=1,
        download_base_url="https://example.com/datasets",
    )
    analytics = AnalyticsConfig(
        metrics_csv=tmp_path / "results" / "metrics.csv",
        dashboard_html=tmp_path / "results" / "dashboard.html",
        compare_dir=tmp_path / "results" / "compare",
    )
    config = EvaluationConfig(
        suites={"lite": suite},
        results_dir=tmp_path / "results",
        dataset_manager=dataset_manager,
        analytics=analytics,
    )

    def fake_run(*args, **kwargs):  # type: ignore[no-redef]
        return DummyProcess()

    monkeypatch.setattr("subprocess.run", fake_run)

    service = EvaluationService(config)
    result = service.run("lite")
    assert result.exit_code == 0
    assert result.output_path.exists()
    assert result.metrics_path.exists()
    assert result.compliance_path.exists()
    assert result.sbom_path and result.sbom_path.exists()
    assert result.telemetry_path and result.telemetry_path.exists()
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    assert metrics["success_rate"] == 0.8
    assert metrics["patch_correct"] == 3
    manifest = json.loads(dataset_manager.manifest_path.read_text(encoding="utf-8"))
    assert "lite" in manifest
