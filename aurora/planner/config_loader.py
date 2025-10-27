"""Load planner configuration from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import CriticConfig, ModelConfig, PlannerConfig, RetryPolicy, SecretRedaction, ExperienceConfig


def load_planner_config(path: Path) -> PlannerConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    primary = ModelConfig(
        provider=data["primary"]["provider"],
        endpoint=data["primary"]["endpoint"],
        model=data["primary"]["model"],
        timeout_seconds=data["primary"].get("timeout_seconds", 120.0),
    )
    critics = tuple(
        CriticConfig(
            name=critic["name"],
            endpoint=critic["endpoint"],
            api_key_env=critic.get("api_key_env"),
            enabled=critic.get("enabled", False),
        )
        for critic in data.get("critic_stack", [])
    )
    retry_policy = RetryPolicy(
        max_attempts=data.get("retry_policy", {}).get("max_attempts", 3),
        backoff_seconds=data.get("retry_policy", {}).get("backoff_seconds", 5),
    )
    redaction_cfg = data.get("secret_redaction", {"enabled": False, "patterns": []})
    redaction = SecretRedaction(
        enabled=redaction_cfg.get("enabled", False),
        patterns=tuple(redaction_cfg.get("patterns", [])),
    )
    experience = None
    if "experience" in data:
        experience = ExperienceConfig(
            path=Path(data["experience"]["path"]),
            limit=data["experience"].get("limit", 5),
        )
    swe_path = Path(data["swe_telemetry_path"]) if data.get("swe_telemetry_path") else None
    raw_policy_notes = data.get("policy_notes", [])
    policy_notes = tuple(note for note in raw_policy_notes if isinstance(note, dict))
    return PlannerConfig(
        primary=primary,
        critics=critics,
        retry_policy=retry_policy,
        secret_redaction=redaction,
        experience_config=experience,
        swe_telemetry_path=swe_path,
        policy_notes=policy_notes,
    )

