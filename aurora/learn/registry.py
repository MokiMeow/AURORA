"""Adapter registry for version management with provenance and signing."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


@dataclass(slots=True)
class AdapterInfo:
    name: str
    version: str
    path: Path
    metadata: dict


class AdapterRegistry:
    def __init__(
        self,
        root: Path,
        schema_path: Optional[Path] = None,
        changelog_path: Optional[Path] = None,
        provenance_path: Optional[Path] = None,
        signing_key_path: Optional[Path] = None,
    ) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._schema = self._load_schema(schema_path)
        self._changelog_path = changelog_path
        self._provenance_path = provenance_path
        self._signing_key = signing_key_path.read_bytes() if signing_key_path and signing_key_path.exists() else None
        self._signing_key_id = signing_key_path.name if signing_key_path else None

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
        metadata = info.metadata | {"name": info.name, "version": info.version}
        self._validate_metadata(metadata)
        if self._signing_key:
            metadata = self._attach_signature(metadata)

        adapter_dir = self._root / info.name / info.version
        adapter_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = adapter_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        self._record_changelog(metadata)
        self._record_provenance(metadata)

    def _load_schema(self, schema_path: Optional[Path]) -> Optional[dict]:
        if not schema_path:
            return None
        try:
            return json.loads(schema_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def _validate_metadata(self, metadata: dict) -> None:
        if not self._schema:
            return
        self._validate_recursive(self._schema, metadata, "metadata")

    def _validate_recursive(self, schema: dict, payload: dict, prefix: str) -> None:
        required = schema.get("required", [])
        for key in required:
            if key not in payload:
                raise ValueError(f"{prefix} missing required key '{key}'")
        properties = schema.get("properties", {})
        for key, subschema in properties.items():
            if key not in payload:
                continue
            value = payload[key]
            if subschema.get("type") == "object" and isinstance(value, dict):
                self._validate_recursive(subschema, value, f"{prefix}.{key}")
            elif subschema.get("type") == "array" and isinstance(value, list):
                # basic item validation: ensure each element is of declared primitive type
                items = subschema.get("items", {})
                item_type = items.get("type")
                expected = _PRIMITIVE_TYPES.get(item_type)
                if expected and not all(isinstance(elem, expected) for elem in value):
                    raise ValueError(f"{prefix}.{key} elements must be of type '{item_type}'")

    def _attach_signature(self, metadata: dict) -> dict:
        payload = json.dumps(metadata, sort_keys=True).encode("utf-8")
        digest = hmac.new(self._signing_key, payload, hashlib.sha256).digest()
        signature = {
            "type": "HMAC-SHA256",
            "value": base64.b64encode(digest).decode("utf-8"),
            "key_id": self._signing_key_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        updated = metadata.copy()
        signatures = list(updated.get("signatures", []))
        signatures.append(signature)
        updated["signatures"] = signatures
        return updated

    def _record_changelog(self, metadata: dict) -> None:
        if not self._changelog_path:
            return
        self._changelog_path.parent.mkdir(parents=True, exist_ok=True)
        entries = []
        if self._changelog_path.exists():
            try:
                entries = json.loads(self._changelog_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                entries = []
        entries.append(
            {
                "name": metadata["name"],
                "version": metadata["version"],
                "timestamp": metadata.get("timestamp"),
                "loss": metadata.get("metrics", {}).get("loss"),
                "accuracy": metadata.get("metrics", {}).get("accuracy"),
            }
        )
        self._changelog_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    def _record_provenance(self, metadata: dict) -> None:
        if not self._provenance_path:
            return
        self._provenance_path.parent.mkdir(parents=True, exist_ok=True)
        entry = metadata.get("provenance", {}) | {
            "name": metadata["name"],
            "version": metadata["version"],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._provenance_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")


_PRIMITIVE_TYPES = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
}
