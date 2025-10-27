"""Federated adapter synchronization utilities."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

LOGGER = logging.getLogger(__name__)


class FederationPolicyError(RuntimeError):
    """Raised when adapter sharing violates policy."""


@dataclass(slots=True)
class FederationConfig:
    peer: str
    endpoint: str
    encryption_enabled: bool
    policy_path: Path
    bias_threshold: float
    allowed_licenses: tuple[str, ...]

    @classmethod
    def from_yaml(cls, path: Path) -> "FederationConfig":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        peers = data.get("peers")
        if not peers:
            raise FederationPolicyError("Federation config missing peers definition")
        peer = peers[0]
        policies = data.get("policies", {})
        license_path = policies.get("licenses")
        allowed = ()
        if license_path:
            license_data = yaml.safe_load(Path(license_path).read_text(encoding="utf-8"))
            allowed = tuple(license_data.get("allow", []))
        return cls(
            peer=peer["name"],
            endpoint=peer.get("endpoint", ""),
            encryption_enabled=data.get("encryption", {}).get("enabled", True),
            policy_path=Path(policies.get("enforcement", "policies/security.yaml")),
            bias_threshold=policies.get("bias_threshold", 0.1),
            allowed_licenses=allowed,
        )


class FederationSync:
    def __init__(self, config: FederationConfig) -> None:
        self._config = config

    def sync(self, adapter_path: Path) -> None:
        LOGGER.info("Syncing adapter %s with peer %s", adapter_path, self._config.peer)
        metadata_path = adapter_path / "metadata.json"
        if not metadata_path.exists():
            raise FederationPolicyError("Adapter metadata missing; cannot sync")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        bias = metadata.get("bias_score", 0.0)
        if bias > self._config.bias_threshold:
            raise FederationPolicyError(
                f"Bias score {bias} exceeds federation threshold {self._config.bias_threshold}"
            )
        license_id = metadata.get("license", "Apache-2.0")
        if self._config.allowed_licenses and license_id not in self._config.allowed_licenses:
            raise FederationPolicyError(f"License {license_id} not allowed for federated sync")
        LOGGER.info("Adapter %s passed federation policy checks", adapter_path)

