"""Tests for dataset manager."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aurora.eval.config import DatasetManagerConfig, SuiteConfig
from aurora.eval.dataset_manager import DatasetManager


def _suite(tmp_path: Path) -> SuiteConfig:
    return SuiteConfig(
        name="lite",
        command=["python", "run.py"],
        dataset_path=tmp_path / "datasets" / "lite",
        artifacts_dir=tmp_path / "artifacts",
        schedule="nightly",
        profile="balanced",
        timeout_minutes=1,
        scenarios=None,
        baseline_metrics=None,
        compare_against=None,
        postprocessors=(),
    )


def test_dataset_manager_downloads_and_records(tmp_path: Path):
    config = DatasetManagerConfig(
        cache_dir=tmp_path / "cache",
        manifest_path=tmp_path / "cache" / "manifest.json",
        auto_update=True,
        ttl_hours=1,
        download_base_url="https://example.com/datasets",
    )
    manager = DatasetManager(config)
    suite = _suite(tmp_path)
    manager.ensure(suite)
    manifest = json.loads(config.manifest_path.read_text(encoding="utf-8"))
    assert "lite" in manifest
    manager.record_result(suite, "run-1", {"success_rate": 0.9})
    manifest = json.loads(config.manifest_path.read_text(encoding="utf-8"))
    assert manifest["lite"]["history"][-1]["run_id"] == "run-1"


def test_dataset_manager_respects_ttl(tmp_path: Path):
    manifest_path = tmp_path / "cache" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "lite": {
                    "name": "lite",
                    "path": "datasets/lite",
                    "last_download": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                    "revision": 1,
                }
            }
        ),
        encoding="utf-8",
    )
    config = DatasetManagerConfig(
        cache_dir=tmp_path / "cache",
        manifest_path=manifest_path,
        auto_update=True,
        ttl_hours=1,
        download_base_url=None,
    )
    manager = DatasetManager(config)
    suite = _suite(tmp_path)
    manager.ensure(suite)
    manifest = json.loads(config.manifest_path.read_text(encoding="utf-8"))
    assert manifest["lite"]["revision"] == 2
