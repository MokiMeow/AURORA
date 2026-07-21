"""Tests for adapter registry."""

import json
from datetime import datetime, timezone
from pathlib import Path

from aurora.learn.registry import AdapterInfo, AdapterRegistry
import pytest


def _base_metadata() -> dict:
    return {
        "name": "default",
        "version": "0.1.0",
        "base_model": "base-model",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "training": {
            "epochs": 1,
            "learning_rate": 0.001,
            "dataset": {
                "path": "experience/log.jsonl",
                "samples": 1,
                "holdout": 0,
                "min_reward": 0.0,
                "stratify": [],
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
                "target_modules": [],
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
            "accuracy": 0.9,
            "bias_score": 0.02,
        },
        "provenance": {"commit": "abc", "branch": "main", "repository": "repo", "artifacts": []},
        "artifacts": {
            "weights": "adapter.safetensors",
            "metrics": "training_metrics.json",
            "bias_report": "bias.json",
        },
    }


def test_adapter_registry_register_and_list(tmp_path: Path):
    changelog = tmp_path / "changelog.json"
    provenance = tmp_path / "provenance.jsonl"
    signing_key = tmp_path / "signing.key"
    signing_key.write_text("super-secret", encoding="utf-8")

    schema_path = Path.cwd() / "configs" / "schemas" / "adapter_metadata.schema.json"
    registry = AdapterRegistry(
        tmp_path,
        schema_path=schema_path,
        changelog_path=changelog,
        provenance_path=provenance,
        signing_key_path=signing_key,
    )

    info = AdapterInfo(
        name="default",
        version="0.1.0",
        path=tmp_path / "default" / "0.1.0",
        metadata=_base_metadata(),
    )
    registry.register(info)

    adapters = list(registry.list_adapters())
    assert len(adapters) == 1
    stored_metadata = adapters[0].metadata
    assert stored_metadata["name"] == "default"
    assert stored_metadata["signatures"]

    changelog_data = json.loads(changelog.read_text(encoding="utf-8"))
    assert changelog_data[0]["version"] == "0.1.0"

    provenance_lines = [json.loads(line) for line in provenance.read_text(encoding="utf-8").splitlines()]
    assert provenance_lines[0]["version"] == "0.1.0"


def test_adapter_registry_rejects_path_escape(tmp_path: Path) -> None:
    registry = AdapterRegistry(tmp_path)
    info = AdapterInfo(
        name="../outside",
        version="0.1.0",
        path=tmp_path,
        metadata={"name": "../outside", "version": "0.1.0"},
    )
    with pytest.raises(ValueError, match="adapter identity"):
        registry.register(info)
