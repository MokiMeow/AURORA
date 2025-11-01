"""Tests for autopilot service."""

from pathlib import Path

from aurora.autopilot import AutopilotConfig, AutopilotService
from aurora.session import SessionManager


def test_autopilot_service_dry_run(tmp_path: Path) -> None:
    eval_config = tmp_path / "eval.yaml"
    results_dir = tmp_path / "results"
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir(parents=True)
    eval_config.write_text(
        f"""
results_dir: {results_dir.as_posix()}
analytics:
  metrics_csv: { (results_dir / "metrics.csv").as_posix() }
  dashboard_html: { (results_dir / "dashboard.html").as_posix() }
  compare_dir: { (results_dir / "compare").as_posix() }
dataset_manager:
  cache_dir: { (tmp_path / "cache").as_posix() }
  manifest_path: { (tmp_path / "cache" / "manifest.json").as_posix() }
  auto_update: false
  ttl_hours: 1
suites:
  lite:
    command: ["python", "-c", "print('ok')"]
    dataset: {dataset_dir.as_posix()}
""",
        encoding="utf-8",
    )
    config = AutopilotConfig(
        session_root=tmp_path / "sessions",
        plan_config=Path("configs/model.yaml"),
        executor_config=Path("configs/ci_profiles.yaml"),
        reward_config=Path("configs/reward.yaml"),
        evaluation_config=eval_config,
        plugins=(),
    )
    service = AutopilotService(config, session_manager=SessionManager(tmp_path / "sessions"))
    report = service.run(task="demo", dry_run=True)
    assert "plan" in report.artifacts
    assert report.artifacts["plan"].exists()
    assert report.duration_seconds >= 0
