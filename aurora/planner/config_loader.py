"""Load planner configuration from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import (
    CriticConfig,
    CriticStrategy,
    ExperienceConfig,
    ModelConfig,
    ModelRoute,
    PlannerConfig,
    RetryPolicy,
    RoutingRule,
    RoutingStrategy,
    SecretRedaction,
)


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

    routes_cfg = data.get("routes", [])
    routes: list[ModelRoute] = []
    for route in routes_cfg:
        routes.append(
            ModelRoute(
                name=route["name"],
                provider=route.get("provider", primary.provider),
                endpoint=route.get("endpoint", primary.endpoint),
                model=route.get("model", primary.model),
                timeout_seconds=route.get("timeout_seconds", primary.timeout_seconds),
                api_key_env=route.get("api_key_env"),
                max_output_tokens=route.get("max_output_tokens"),
                keywords=tuple(route.get("keywords", [])),
                capabilities=tuple(route.get("capabilities", [])),
                extra=route.get("extra"),
            )
        )
    primary_route = ModelRoute(
        name="primary",
        provider=primary.provider,
        endpoint=primary.endpoint,
        model=primary.model,
        timeout_seconds=primary.timeout_seconds,
    )
    if not any(route.name == primary_route.name for route in routes):
        routes.insert(0, primary_route)

    routing_cfg = data.get("routing") or {}
    default_route = routing_cfg.get("default_route") or routes[0].name
    rules = tuple(
        RoutingRule(
            name=rule.get("name", rule.get("route", "rule")),
            route=rule["route"],
            keywords=tuple(rule.get("keywords", [])),
            auto_only=rule.get("auto_only", False),
        )
        for rule in routing_cfg.get("rules", [])
    )
    routing = RoutingStrategy(default_route=default_route, rules=rules) if routes else None

    critic_strategy_cfg = data.get("critic_strategy", {})
    critic_strategy = CriticStrategy(
        mode=critic_strategy_cfg.get("mode", "all"),
        threshold=critic_strategy_cfg.get("threshold"),
        priority=tuple(critic_strategy_cfg.get("priority", [])),
    )

    return PlannerConfig(
        primary=primary,
        critics=critics,
        retry_policy=retry_policy,
        secret_redaction=redaction,
        experience_config=experience,
        swe_telemetry_path=swe_path,
        policy_notes=policy_notes,
        routes=tuple(routes),
        routing=routing,
        critic_strategy=critic_strategy,
    )

