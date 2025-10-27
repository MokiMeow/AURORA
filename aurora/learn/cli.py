"""CLI helpers for adapter management."""

from __future__ import annotations

from pathlib import Path

from .registry import AdapterRegistry


def list_adapters(root: Path) -> list[dict]:
    registry = AdapterRegistry(root)
    return [info.metadata for info in registry.list_adapters()]

