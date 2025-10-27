"""Planner configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int
    backoff_seconds: int


@dataclass(slots=True)
class SecretRedaction:
    enabled: bool
    patterns: tuple[str, ...]


@dataclass(slots=True)
class CriticConfig:
    name: str
    endpoint: str
    api_key_env: str | None = None
    enabled: bool = False


@dataclass(slots=True)
class ModelConfig:
    provider: str
    endpoint: str
    model: str
    timeout_seconds: float


@dataclass(slots=True)
class ExperienceConfig:
    path: Path
    limit: int = 5


@dataclass(slots=True)
class PlannerConfig:
    primary: ModelConfig
    critics: tuple[CriticConfig, ...]
    retry_policy: RetryPolicy
    secret_redaction: SecretRedaction
    experience_config: ExperienceConfig | None = None
    swe_telemetry_path: Path | None = None
    policy_notes: tuple[dict[str, Any], ...] = ()

