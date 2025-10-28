"""Federated adapter synchronization utilities."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

LOGGER = logging.getLogger(__name__)


class FederationPolicyError(RuntimeError):
    """Raised when adapter sharing violates policy."""


@dataclass(slots=True)
class FederationConfig:
    peer: str
    endpoint: str
    public_key: Optional[str]
    encryption_enabled: bool
    encryption_method: str
    encryption_key_path: Optional[Path]
    policy_path: Path
    bias_threshold: float
    allowed_licenses: tuple[str, ...]
    audit_log_path: Path

    @classmethod
    def from_yaml(cls, path: Path) -> "FederationConfig":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        peers = data.get("peers")
        if not peers:
            raise FederationPolicyError("Federation config missing peers definition")
        peer = peers[0]
        policies = data.get("policies", {})
        license_path = policies.get("licenses")
        allowed: tuple[str, ...] = ()
        if license_path:
            license_data = yaml.safe_load(Path(license_path).read_text(encoding="utf-8"))
            allowed = tuple(license_data.get("allow", []))
        encryption_section = data.get("encryption", {})
        audit_log = policies.get("audit_log", "artifacts/federation/audit.jsonl")
        return cls(
            peer=peer["name"],
            endpoint=peer.get("endpoint", ""),
            public_key=peer.get("public_key"),
            encryption_enabled=encryption_section.get("enabled", True),
            encryption_method=encryption_section.get("method", "age"),
            encryption_key_path=(Path(encryption_section["key_path"]) if encryption_section.get("key_path") else None),
            policy_path=Path(policies.get("enforcement", "policies/security.yaml")),
            bias_threshold=policies.get("bias_threshold", 0.1),
            allowed_licenses=allowed,
            audit_log_path=Path(audit_log),
        )


class FederationSync:
    def __init__(self, config: FederationConfig) -> None:
        self._config = config

    def sync(self, adapter_path: Path) -> None:
        LOGGER.info("Syncing adapter %s with peer %s", adapter_path, self._config.peer)
        metadata = self._load_metadata(adapter_path)
        self._enforce_policies(metadata)
        self._record_audit(metadata)
        LOGGER.info("Adapter %s passed federation policy checks", adapter_path)

    def _load_metadata(self, adapter_path: Path) -> dict:
        metadata_path = adapter_path / "metadata.json"
        if not metadata_path.exists():
            raise FederationPolicyError("Adapter metadata missing; cannot sync")
        return json.loads(metadata_path.read_text(encoding="utf-8"))

    def _enforce_policies(self, metadata: dict) -> None:
        bias = metadata.get("metrics", {}).get("bias_score", metadata.get("bias_score", 0.0))
        if bias > self._config.bias_threshold:
            raise FederationPolicyError(
                f"Bias score {bias} exceeds federation threshold {self._config.bias_threshold}"
            )
        license_id = metadata.get("license", "Apache-2.0")
        if self._config.allowed_licenses and license_id not in self._config.allowed_licenses:
            raise FederationPolicyError(f"License {license_id} not allowed for federated sync")
        if self._config.encryption_enabled:
            self._validate_encryption()

    def _validate_encryption(self) -> None:
        if not self._config.encryption_key_path or not self._config.encryption_key_path.exists():
            raise FederationPolicyError("Encryption key material missing for federation sync")

    def _record_audit(self, metadata: dict) -> None:
        self._config.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "peer": self._config.peer,
            "endpoint": self._config.endpoint,
            "adapter": {
                "name": metadata.get("name"),
                "version": metadata.get("version"),
                "license": metadata.get("license"),
            },
            "bias_score": metadata.get("metrics", {}).get("bias_score", metadata.get("bias_score")),
            "encryption": {
                "enabled": self._config.encryption_enabled,
                "method": self._config.encryption_method,
            },
        }
        with self._config.audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
