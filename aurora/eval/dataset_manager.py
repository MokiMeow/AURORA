"""Dataset management utilities for evaluation suites."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

from .config import DatasetManagerConfig, SuiteConfig

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class DatasetManager:
    config: DatasetManagerConfig

    def ensure(self, suite: SuiteConfig) -> None:
        """Ensure the dataset for the suite is available and up to date."""
        manifest = self._load_manifest()
        entry = manifest.get(suite.name, {})
        dataset_path = suite.dataset_path
        dataset_path.mkdir(parents=True, exist_ok=True)
        if self._needs_refresh(entry):
            self._download_dataset(suite, dataset_path)
            entry = {
                "name": suite.name,
                "path": str(dataset_path),
                "last_download": datetime.now(timezone.utc).isoformat(),
                "revision": entry.get("revision", 0) + 1,
            }
            manifest[suite.name] = entry
            self._write_manifest(manifest)

    def record_result(self, suite: SuiteConfig, run_id: str, metrics: dict[str, Any]) -> None:
        manifest = self._load_manifest()
        entry = manifest.get(suite.name, {})
        history = entry.get("history", [])
        history.append(
            {
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": metrics,
            }
        )
        entry["history"] = history[-20:]
        manifest[suite.name] = entry
        self._write_manifest(manifest)

    def _needs_refresh(self, entry: Dict[str, Any]) -> bool:
        if not entry:
            return True
        if not self.config.auto_update:
            return False
        last_download = entry.get("last_download")
        if not last_download:
            return True
        try:
            last_dt = datetime.fromisoformat(last_download)
        except ValueError:
            return True
        expiry = last_dt + timedelta(hours=self.config.ttl_hours)
        return datetime.now(timezone.utc) > expiry

    def _download_dataset(self, suite: SuiteConfig, dataset_path: Path) -> None:
        dataset_path.mkdir(parents=True, exist_ok=True)
        marker = dataset_path / ".aurora_dataset"
        content = {
            "suite": suite.name,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "source": self.config.download_base_url,
        }
        marker.write_text(json.dumps(content, indent=2), encoding="utf-8")
        LOGGER.info("Prepared dataset %s at %s", suite.name, dataset_path)

    def _load_manifest(self) -> Dict[str, Any]:
        path = self.config.manifest_path
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write_manifest(self, manifest: Dict[str, Any]) -> None:
        path = self.config.manifest_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
