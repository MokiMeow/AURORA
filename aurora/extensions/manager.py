"""Extension loading utilities."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence

from .base import AuroraExtension


@dataclass(slots=True)
class ExtensionManager:
    extensions: List[AuroraExtension] = field(default_factory=list)

    def load_many(self, specs: Sequence[str]) -> None:
        for spec in specs:
            extension = self._load_spec(spec)
            self.extensions.append(extension)

    def _load_spec(self, spec: str) -> AuroraExtension:
        if ":" not in spec:
            raise ValueError(f"Invalid extension spec '{spec}', expected module:Class")
        module_name, class_name = spec.split(":", 1)
        module = importlib.import_module(module_name)
        extension_cls = getattr(module, class_name)
        instance = extension_cls()  # type: ignore[call-arg]
        if not isinstance(instance, AuroraExtension):
            raise TypeError(f"Extension {spec} does not implement AuroraExtension")
        return instance  # type: ignore[return-value]

    @classmethod
    def from_config(cls, path: Path) -> "ExtensionManager":
        if not path.exists():
            return cls()
        specs: List[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            specs.append(line)
        manager = cls()
        manager.load_many(specs)
        return manager

    def iter_by_type(self, extension_type: type) -> Iterable[AuroraExtension]:
        for extension in self.extensions:
            if isinstance(extension, extension_type):
                yield extension
