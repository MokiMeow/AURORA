"""Tests for adapter CLI helpers."""

import json
from datetime import datetime, timezone
from pathlib import Path

from aurora.learn.cli import list_adapters, sync_adapter, rollback_adapter, publish_adapter
from aurora.learn.registry import AdapterRegistry, AdapterInfo


def _seed_adapter(root: Path, name: str = "core", version: str = "0.1.0") -> Path:
    registry = AdapterRegistry(root)
    metadata = {
        "name": name,
        "version": version,
        "bias_score": 0.05,
        "metrics": {"loss": 0.1, "accuracy": 0.95},
        "license": "Apache-2.0",
    }
    info = AdapterInfo(name=name, version=version, path=root / name / version, metadata=metadata)
    registry.register(info)
    info.path.mkdir(parents=True, exist_ok=True)
    (info.path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return info.path


def _write_license_policy(root: Path) -> Path:
    policy = root / "license.yaml"
    policy.write_text("allow:\n  - Apache-2.0\n", encoding="utf-8")
    return policy


def _write_federation_config(root: Path, license_policy: Path, key_path: Path, audit_path: Path) -> Path:
    config_path = root / "federation.yaml"
    config_path.write_text(
        f"""
peers:
  - name: test-peer
    endpoint: https://example.com
policies:
  bias_threshold: 0.2
  licenses: {license_policy}
  enforcement: policies/security.yaml
  audit_log: {audit_path}
encryption:
  enabled: true
  method: age
  key_path: {key_path}
""",
        encoding="utf-8",
    )
    return config_path


def _metadata_payload(name: str = "core", version: str = "0.2.0") -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "name": name,
        "version": version,
        "base_model": "base-model",
        "timestamp": timestamp,
        "license": "Apache-2.0",
        "training": {
            "epochs": 1,
            "learning_rate": 0.001,
            "dataset": {
                "path": "experience/log.jsonl",
                "samples": 4,
                "holdout": 1,
                "min_reward": 0.1,
                "stratify": ["reward"],
            },
            "device": {
                "type": "cpu",
                "gpu_memory_gb": 0,
                "mixed_precision": "bf16",
                "gradient_checkpointing": False,
            },
            "lora": {
                "rank": 4,
                "alpha": 8,
                "dropout": 0.1,
                "target_modules": ["q_proj"],
                "target_pattern": [],
                "scaling": 1.0,
            },
            "accelerate": {
                "mixed_precision": "bf16",
                "gradient_accumulation_steps": 1,
                "compile_model": False,
            },
        },
        "metrics": {
            "loss": 0.1,
            "accuracy": 0.96,
            "bias_score": 0.03,
        },
        "provenance": {"commit": "abc", "branch": "main", "repository": "repo", "artifacts": []},
        "artifacts": {
            "weights": "adapter.safetensors",
            "metrics": "training_metrics.json",
            "bias_report": "bias.json",
        },
    }


def test_list_adapters(tmp_path: Path):
    _seed_adapter(tmp_path)
    adapters = list_adapters(tmp_path)
    assert adapters
    assert adapters[0]["name"] == "core"


def test_sync_adapter_enforces_policy(tmp_path: Path):
    _seed_adapter(tmp_path)
    license_policy = _write_license_policy(tmp_path)
    key_file = tmp_path / "federation.key"
    key_file.write_text("secret", encoding="utf-8")
    audit_path = tmp_path / "audit.jsonl"
    policy_path = _write_federation_config(tmp_path, license_policy, key_file, audit_path)
    metadata = sync_adapter(tmp_path, "core", "0.1.0", policy_path)
    assert metadata["version"] == "0.1.0"
    assert audit_path.exists()


def test_publish_adapter_registers_metadata(tmp_path: Path):
    metadata = _metadata_payload()
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    published = publish_adapter(tmp_path, metadata_path)
    stored = json.loads((tmp_path / metadata["name"] / metadata["version"] / "metadata.json").read_text(encoding="utf-8"))
    assert published["version"] == metadata["version"]
    assert stored["base_model"] == "base-model"


def test_rollback_adapter(tmp_path: Path):
    path = _seed_adapter(tmp_path)
    resolved = rollback_adapter(tmp_path, "core", "0.1.0")
    assert resolved == path
