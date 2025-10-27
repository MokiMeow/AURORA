"""Adapter registry for version management."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class AdapterInfo:
    name: str
    version: str
    path: Path
    metadata: dict


class AdapterRegistry:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def list_adapters(self) -> Iterable[AdapterInfo]:
        for directory in self._root.glob("**/*"):
            if directory.is_dir():
                metadata = directory / "metadata.json"
                if metadata.exists():
                    data = json.loads(metadata.read_text(encoding="utf-8"))
                    yield AdapterInfo(
                        name=data["name"],
                        version=data["version"],
                        path=directory,
                        metadata=data,
                    )

    def register(self, info: AdapterInfo) -> None:
        adapter_dir = self._root / info.name / info.version
        adapter_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = adapter_dir / "metadata.json"
        metadata_path.write_text(json.dumps(info.metadata, indent=2), encoding="utf-8")

