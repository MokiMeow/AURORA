"""CLI helpers for adapter management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .registry import AdapterRegistry
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
    path = root / name / version
    if not path.exists():
        raise ValueError("Adapter version not available for rollback")
    PDCAEntry(
        phase="Learn",
        event="cli_rollback",
        payload={"adapter": version, "name": name},
    )
    return path

