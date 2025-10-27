"""Tests for adapter CLI helpers."""

import json
from pathlib import Path

import pytest

from aurora.learn.cli import list_adapters, sync_adapter, rollback_adapter
from aurora.learn.registry import AdapterRegistry, AdapterInfo


def _seed_adapter(root: Path, name: str = "core", version: str = "0.1.0") -> Path:
    registry = AdapterRegistry(root)
    info = AdapterInfo(
        name=name,
        version=version,
        path=root / name / version,
        metadata={
            "name": name,
            "version": version,
            "bias_score": 0.05,
            "license": "Apache-2.0",
        },
    )
    registry.register(info)
    (info.path / "metadata.json").write_text(json.dumps(info.metadata), encoding="utf-8")
    return info.path


def _write_license_policy(root: Path) -> Path:
    policy = root / "license.yaml"
    policy.write_text("allow:\n  - Apache-2.0\n", encoding="utf-8")
    return policy


def test_list_adapters(tmp_path: Path):
    _seed_adapter(tmp_path)
    adapters = list_adapters(tmp_path)
    assert adapters
    assert adapters[0]["name"] == "core"


def test_sync_adapter_enforces_policy(tmp_path: Path):
    _seed_adapter(tmp_path)
    license_policy = _write_license_policy(tmp_path)
    policy_path = tmp_path / "federation.yaml"
    policy_path.write_text(
        f"""
peers:
  - name: test-peer
    endpoint: https://example.com
policies:
  bias_threshold: 0.2
  licenses: {license_policy}
  enforcement: policies/security.yaml
encryption:
  enabled: true
""",
        encoding="utf-8",
    )
    metadata = sync_adapter(tmp_path, "core", "0.1.0", policy_path)
    assert metadata["version"] == "0.1.0"


def test_rollback_adapter(tmp_path: Path):
    path = _seed_adapter(tmp_path)
    resolved = rollback_adapter(tmp_path, "core", "0.1.0")
    assert resolved == path
