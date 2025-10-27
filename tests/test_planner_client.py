"\"\"\"Tests for planner client routing and providers.\"\"\""

from __future__ import annotations

import json

import httpx
import pytest

from aurora.planner.client import PlannerClient, PlannerResponse
from aurora.planner.config import (
    CriticConfig,
    CriticStrategy,
    ModelConfig,
    ModelRoute,
    PlannerConfig,
    RetryPolicy,
    SecretRedaction,
)


def _base_config() -> PlannerConfig:
    primary = ModelConfig(
        provider="ollama",
        endpoint="http://localhost:11434/api/generate",
        model="deepseek-r1:7b",
        timeout_seconds=30,
    )
    return PlannerConfig(
        primary=primary,
        critics=(CriticConfig(name="critic", endpoint="http://critic", enabled=False),),
        retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=0),
        secret_redaction=SecretRedaction(enabled=True, patterns=("API_KEY",)),
        experience_config=None,
        swe_telemetry_path=None,
        policy_notes=(),
        routes=(),
        routing=None,
        critic_strategy=CriticStrategy(mode="all"),
    )


@pytest.mark.asyncio
async def test_generate_openai_route(monkeypatch):
    route = ModelRoute(
        name="openai",
        provider="openai",
        endpoint="https://api.openai.com/v1/chat/completions",
        model="gpt-4o-mini",
        timeout_seconds=20,
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        assert payload["model"] == route.model
        assert payload["messages"][0]["content"] == "hello"
        data = {"choices": [{"message": {"content": "world"}}]}
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    client = PlannerClient(_base_config(), client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs))
    response: PlannerResponse = await client.generate("hello", route=route, metadata={}, stream=False)
    assert response.content == "world"
    assert response.provider == "openai"


@pytest.mark.asyncio
async def test_generate_streaming_event(monkeypatch):
    route = ModelRoute(
        name="ollama",
        provider="ollama",
        endpoint="http://localhost:11434/api/generate",
        model="deepseek-r1:7b",
        timeout_seconds=10,
    )

    body = "data: {\"response\": \"Hel\"}\ndata: {\"response\": \"lo\"}\n"

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=body)

    transport = httpx.MockTransport(handler)
    client = PlannerClient(_base_config(), client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs))
    response = await client.generate("hello", route=route, metadata={}, stream=True)
    assert response.content == "Hello"


@pytest.mark.asyncio
async def test_critic_outcome_quorum(monkeypatch):
    config = _base_config()
    config.critics = (
        CriticConfig(name="c1", endpoint="http://critic1", enabled=True),
        CriticConfig(name="c2", endpoint="http://critic2", enabled=True),
    )
    config.critic_strategy = CriticStrategy(mode="quorum", threshold=1)

    async def fake_call(self, critic, payload):  # type: ignore[no-untyped-def]
        status = "pass" if critic.name == "c1" else "fail"
        return {"critic": critic.name, "response": {"status": status}}

    client = PlannerClient(config, client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})), **kw))
    monkeypatch.setattr(PlannerClient, "_call_critic", fake_call)
    outcome = await client.run_critics({"test": True})
    assert outcome.accepted is True
    assert len(outcome.results) == 2
