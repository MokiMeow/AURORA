"""Tests for adapter registry."""

from pathlib import Path

from aurora.learn.registry import AdapterRegistry, AdapterInfo


def test_adapter_registry_register_and_list(tmp_path: Path):
    registry = AdapterRegistry(tmp_path)
    info = AdapterInfo(
        name="default",
        version="0.1.0",
        path=tmp_path / "default" / "0.1.0",
        metadata={"name": "default", "version": "0.1.0"},
    )
    registry.register(info)
    adapters = list(registry.list_adapters())
    assert len(adapters) == 1
    assert adapters[0].name == "default"

