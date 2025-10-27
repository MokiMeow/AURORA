"""Tests for planner router."""

from aurora.planner.config import (
    CriticStrategy,
    ModelConfig,
    ModelRoute,
    PlannerConfig,
    RetryPolicy,
    RoutingRule,
    RoutingStrategy,
    SecretRedaction,
)
from aurora.planner.router import PlannerRouter


def _base_config() -> PlannerConfig:
    primary = ModelConfig(
        provider="ollama",
        endpoint="http://localhost:11434/api/generate",
        model="deepseek-r1:7b",
        timeout_seconds=60,
    )
    routes = (
        ModelRoute(
            name="primary",
            provider="ollama",
            endpoint=primary.endpoint,
            model=primary.model,
            timeout_seconds=primary.timeout_seconds,
        ),
        ModelRoute(
            name="cloud",
            provider="openai",
            endpoint="https://api.openai.com/v1/chat/completions",
            model="gpt-4o-mini",
            timeout_seconds=45,
            keywords=("security",),
        ),
    )
    routing = RoutingStrategy(
        default_route="primary",
        rules=(
            RoutingRule(name="security", route="cloud", keywords=("security",)),
        ),
    )
    return PlannerConfig(
        primary=primary,
        critics=tuple(),
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=1),
        secret_redaction=SecretRedaction(enabled=False, patterns=()),
        experience_config=None,
        swe_telemetry_path=None,
        policy_notes=(),
        routes=routes,
        routing=routing,
        critic_strategy=CriticStrategy(),
    )


def test_router_selects_default_when_no_rule_matches():
    router = PlannerRouter(_base_config())
    route = router.select_route("Refactor parser", [], auto=False)
    assert route.name == "primary"


def test_router_selects_rule_when_keywords_match():
    router = PlannerRouter(_base_config())
    route = router.select_route("Improve security audit", [], auto=False)
    assert route.name == "cloud"
