"""Extension registry helpers for marketplace-style workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(slots=True)
class ExtensionManifest:
    """Metadata stored for a registry entry."""

    name: str
    spec: str
    version: str
    signature: str | None
    path: Path


class ExtensionRegistry:
    """Persisted registry of locally installed extensions."""

    def __init__(self, registry_path: Path | None = None) -> None:
        self._path = registry_path or Path("artifacts/extensions/registry.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._registry = self._load()

    def add(self, name: str, spec: str, source_path: Path, version: str = "0.1.0") -> ExtensionManifest:
        manifest = ExtensionManifest(
            name=name,
            spec=spec,
            version=version,
            signature=self._sign(source_path),
            path=source_path,
        )
        self._registry[name] = {
            "name": manifest.name,
            "spec": manifest.spec,
            "version": manifest.version,
            "signature": manifest.signature,
            "path": str(manifest.path),
        }
        self._persist()
        return manifest

    def remove(self, name: str) -> None:
        if name in self._registry:
            del self._registry[name]
            self._persist()

    def get(self, name: str) -> Optional[ExtensionManifest]:
        entry = self._registry.get(name)
        if not entry:
            return None
        return ExtensionManifest(
            name=entry["name"],
            spec=entry["spec"],
            version=entry.get("version", "0.1.0"),
            signature=entry.get("signature"),
            path=Path(entry["path"]),
        )

    def list(self) -> List[ExtensionManifest]:
        manifests = [manifest for name in self._registry if (manifest := self.get(name)) is not None]
        return sorted(manifests, key=lambda manifest: manifest.name)

    def load_specs(self) -> List[str]:
        return [entry["spec"] for entry in self._registry.values()]

    def _sign(self, path: Path) -> str:
        hasher = sha256()
        if path.is_file():
            hasher.update(path.read_bytes())
        else:
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    hasher.update(child.read_bytes())
        return hasher.hexdigest()

    def _persist(self) -> None:
        self._path.write_text(json.dumps(self._registry, indent=2), encoding="utf-8")

    def _load(self) -> Dict[str, dict]:
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))
