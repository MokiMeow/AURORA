"""CLI helpers for adapter management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aurora.paths import resolve_within

from .registry import AdapterRegistry, AdapterInfo
from .federation import FederationSync, FederationConfig
from ..planner.pdca import PDCAEntry


def list_adapters(root: Path) -> list[dict[str, Any]]:
    registry = AdapterRegistry(root)
    return [info.metadata for info in registry.list_adapters()]


def sync_adapter(root: Path, name: str, version: str, config_path: Path) -> dict[str, Any]:
    registry = AdapterRegistry(root)
    adapters = list(registry.list_adapters())
    matching = next((adapter for adapter in adapters if adapter.name == name and adapter.version == version), None)
    if not matching:
        raise ValueError("Adapter not found for sync")
    config = FederationConfig.from_yaml(config_path)
    FederationSync(config).sync(matching.path)
    PDCAEntry(
        phase="Learn",
        event="cli_sync",
        payload={"adapter": version, "peer": config.peer},
    )
    return matching.metadata


def rollback_adapter(root: Path, name: str, version: str) -> Path:
    path = resolve_within(root, name, version, label="adapter identity")
    if not path.exists():
        raise ValueError("Adapter version not available for rollback")
    PDCAEntry(
        phase="Learn",
        event="cli_rollback",
        payload={"adapter": version, "name": name},
    )
    return path


def publish_adapter(root: Path, metadata_path: Path, schema_path: Path | None = None) -> dict[str, Any]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    schema = schema_path or Path("configs/schemas/adapter_metadata.schema.json")
    registry = AdapterRegistry(root, schema_path=schema)
    adapter_dir = resolve_within(
        root,
        metadata["name"],
        metadata["version"],
        label="adapter identity",
    )
    adapter_dir.mkdir(parents=True, exist_ok=True)
    (adapter_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    info = AdapterInfo(
        name=metadata["name"],
        version=metadata["version"],
        path=adapter_dir,
        metadata=metadata,
    )
    registry.register(info)
    PDCAEntry(
        phase="Learn",
        event="cli_publish",
        payload={"adapter": metadata["version"], "name": metadata["name"]},
    )
    return metadata
