"""Tests for evaluation service."""

import json
from pathlib import Path

from aurora.eval.config import EvaluationConfig, SuiteConfig
from aurora.eval.service import EvaluationService


class DummyProcess:
    def __init__(self) -> None:
        self.returncode = 0
        self.stdout = "METRIC:success_rate=0.8\nMETRIC:latency=120"
        self.stderr = ""


def test_evaluation_service_runs_and_generates_artifacts(monkeypatch, tmp_path: Path):
    suite = SuiteConfig(
        name="lite",
        command=["python", "run.py"],
        dataset_path=tmp_path,
        artifacts_dir=tmp_path / "artifacts",
        schedule="nightly",
        profile="balanced",
        timeout_minutes=1,
    )
    config = EvaluationConfig(suites={"lite": suite}, results_dir=tmp_path / "results")

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

