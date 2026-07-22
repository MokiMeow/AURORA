"""Planner configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    provider: str | None = None


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
class ModelRoute:
    name: str
    provider: str
    endpoint: str
    model: str
    timeout_seconds: float
    api_key_env: str | None = None
    max_output_tokens: int | None = None
    keywords: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    extra: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.extra is None:
            self.extra = {}


@dataclass(slots=True)
class RoutingRule:
    name: str
    route: str
    keywords: tuple[str, ...] = ()
    auto_only: bool = False


@dataclass(slots=True)
class RoutingStrategy:
    default_route: str
    rules: tuple[RoutingRule, ...] = ()


@dataclass(slots=True)
class CriticStrategy:
    mode: str = "all"
    threshold: int | None = None
    priority: tuple[str, ...] = ()


@dataclass(slots=True)
class PlannerConfig:
    primary: ModelConfig
    critics: tuple[CriticConfig, ...]
    retry_policy: RetryPolicy
    secret_redaction: SecretRedaction
    experience_config: ExperienceConfig | None = None
    swe_telemetry_path: Path | None = None
    policy_notes: tuple[dict[str, Any], ...] = ()
    routes: tuple[ModelRoute, ...] = ()
    routing: RoutingStrategy | None = None
    critic_strategy: CriticStrategy = field(default_factory=CriticStrategy)

