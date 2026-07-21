"""High-level helpers for managing model routing configurations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

import yaml


@dataclass(slots=True)
class ModelProfile:
    name: str
    provider: str
    endpoint: str
    model: str


class ModelManager:
    """Read and mutate model routing config files."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path("configs/model.yaml")
        if not self._path.exists():
            raise FileNotFoundError(f"Model config not found at {self._path}")
        self._data = yaml.safe_load(self._path.read_text(encoding="utf-8"))

    def list_profiles(self) -> List[ModelProfile]:
        routes = self._data.get("routes", [])
        profiles: List[ModelProfile] = []
        for route in routes:
            profiles.append(
                ModelProfile(
                    name=route["name"],
                    provider=route["provider"],
                    endpoint=route["endpoint"],
                    model=route["model"],
                )
            )
        return profiles

    def default_profile(self) -> str:
        return self._data.get("routing", {}).get("default_route", "")

    def switch(self, profile: str) -> None:
        routes = {route["name"]: route for route in self._data.get("routes", [])}
        if profile not in routes:
            raise ValueError(f"Profile '{profile}' not defined in routes.")
        self._data.setdefault("routing", {})["default_route"] = profile
        self._persist()

    def test(self, profile: str) -> dict[str, Any]:
        routes = {route["name"]: route for route in self._data.get("routes", [])}
        if profile not in routes:
            raise ValueError(f"Profile '{profile}' not defined in routes.")
        route = routes[profile]
        payload = {
            "profile": profile,
            "provider": route["provider"],
            "endpoint": route["endpoint"],
            "model": route["model"],
            "timeout": route.get("timeout_seconds"),
        }
        return payload

    def add_route(self, route: dict[str, Any]) -> None:
        routes = self._data.setdefault("routes", [])
        routes.append(route)
        self._persist()

    def save_snapshot(self, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def _persist(self) -> None:
        self._path.write_text(yaml.safe_dump(self._data, sort_keys=False), encoding="utf-8")
