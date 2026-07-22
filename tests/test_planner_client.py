"""Tests for planner client routing and providers."""

from __future__ import annotations

import json

import httpx
import pytest

from aurora.planner.client import PlannerClient, PlannerError, PlannerResponse
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
async def test_generate_ollama_request_body() -> None:
    route = ModelRoute(
        name="ollama",
        provider="ollama",
        endpoint="http://localhost:11434/api/generate",
        model="deepseek-r1:7b",
        timeout_seconds=20,
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == {
            "model": "deepseek-r1:7b",
            "prompt": "hello",
            "stream": True,
        }
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"response": "world"})

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )

    response = await client.generate("hello", route=route, metadata={"ignored": True})

    assert response.content == "world"


@pytest.mark.asyncio
async def test_generate_openai_request_body_and_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_TEST_KEY", "openai-secret")
    route = ModelRoute(
        name="openai",
        provider="openai",
        endpoint="https://api.openai.com/v1/chat/completions",
        model="gpt-4o-mini",
        timeout_seconds=20,
        api_key_env="OPENAI_TEST_KEY",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
            "metadata": {"purpose": "test"},
        }
        assert request.headers["authorization"] == "Bearer openai-secret"
        assert "x-api-key" not in request.headers
        data = {"choices": [{"message": {"content": "world"}}]}
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )
    response: PlannerResponse = await client.generate(
        "hello", route=route, metadata={"purpose": "test"}, stream=False
    )
    assert response.content == "world"
    assert response.provider == "openai"


@pytest.mark.asyncio
async def test_generate_anthropic_request_body_and_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_TEST_KEY", "anthropic-secret")
    route = ModelRoute(
        name="anthropic",
        provider="anthropic",
        endpoint="https://api.anthropic.com/v1/messages",
        model="claude-test",
        timeout_seconds=20,
        api_key_env="ANTHROPIC_TEST_KEY",
        max_output_tokens=256,
        extra={"api_version": "2024-01-01", "temperature": 0},
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == {
            "model": "claude-test",
            "max_tokens": 256,
            "stream": True,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "hello"}]}
            ],
            "temperature": 0,
        }
        assert request.headers["x-api-key"] == "anthropic-secret"
        assert request.headers["anthropic-version"] == "2024-01-01"
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"content": [{"type": "text", "text": "world"}]})

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )

    response = await client.generate("hello", route=route)

    assert response.content == "world"


@pytest.mark.asyncio
async def test_generate_gemini_request_body_and_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_TEST_KEY", "gemini-secret")
    route = ModelRoute(
        name="gemini",
        provider="gemini",
        endpoint="https://generativelanguage.googleapis.com/v1beta/models/test:generateContent",
        model="gemini-test",
        timeout_seconds=20,
        api_key_env="GEMINI_TEST_KEY",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == {
            "contents": [{"role": "user", "parts": [{"text": "hello"}]}]
        }
        assert request.headers["x-goog-api-key"] == "gemini-secret"
        assert "authorization" not in request.headers
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "world"}]}}]},
        )

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )

    response = await client.generate("hello", route=route, stream=False)

    assert response.content == "world"


@pytest.mark.asyncio
async def test_missing_cloud_credential_fails_before_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MISSING_OPENAI_KEY", raising=False)
    calls = 0
    route = ModelRoute(
        name="openai",
        provider="openai",
        endpoint="https://api.openai.com/v1/chat/completions",
        model="gpt-4o-mini",
        timeout_seconds=20,
        api_key_env="MISSING_OPENAI_KEY",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )

    with pytest.raises(PlannerError, match="Missing credential environment variable"):
        await client.generate("hello", route=route)

    assert calls == 0


@pytest.mark.asyncio
async def test_nonretryable_401_makes_one_request_and_sanitizes_error() -> None:
    calls = 0
    route = ModelRoute(
        name="ollama",
        provider="ollama",
        endpoint="http://provider.test/generate",
        model="test",
        timeout_seconds=10,
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            401,
            headers={"x-request-id": "request-401"},
            text="sensitive-provider-body",
        )

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )

    with pytest.raises(PlannerError) as error:
        await client.generate("hello", route=route)

    assert calls == 1
    assert "status 401" in str(error.value)
    assert "request-401" in str(error.value)
    assert "sensitive-provider-body" not in str(error.value)


@pytest.mark.asyncio
async def test_429_retries_and_honors_retry_after() -> None:
    calls = 0
    sleeps: list[float] = []
    route = ModelRoute(
        name="ollama",
        provider="ollama",
        endpoint="http://provider.test/generate",
        model="test",
        timeout_seconds=10,
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"retry-after": "7"})
        return httpx.Response(200, json={"response": "recovered"})

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
        sleep=fake_sleep,
    )

    response = await client.generate("hello", route=route)

    assert response.content == "recovered"
    assert calls == 2
    assert sleeps == [7.0]


@pytest.mark.asyncio
async def test_501_retries_to_configured_attempt_count() -> None:
    calls = 0
    sleeps: list[float] = []
    route = ModelRoute(
        name="ollama",
        provider="ollama",
        endpoint="http://provider.test/generate",
        model="test",
        timeout_seconds=10,
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(501)

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
        sleep=fake_sleep,
    )

    with pytest.raises(PlannerError, match="after 2 attempts"):
        await client.generate("hello", route=route)

    assert calls == 2
    assert sleeps == [0.0]


@pytest.mark.asyncio
async def test_timeout_recovers_on_retry() -> None:
    calls = 0
    sleeps: list[float] = []
    route = ModelRoute(
        name="ollama",
        provider="ollama",
        endpoint="http://provider.test/generate",
        model="test",
        timeout_seconds=10,
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json={"response": "recovered"})

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
        sleep=fake_sleep,
    )

    response = await client.generate("hello", route=route)

    assert response.content == "recovered"
    assert calls == 2
    assert sleeps == [0.0]


@pytest.mark.asyncio
async def test_exhausted_transport_retries_are_bounded() -> None:
    calls = 0
    sleeps: list[float] = []
    config = _base_config()
    config.retry_policy = RetryPolicy(max_attempts=3, backoff_seconds=40)
    route = ModelRoute(
        name="ollama",
        provider="ollama",
        endpoint="http://provider.test/generate",
        model="test",
        timeout_seconds=10,
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectTimeout("timed out", request=request)

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        config,
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
        sleep=fake_sleep,
    )

    with pytest.raises(PlannerError, match="after 3 attempts"):
        await client.generate("hello", route=route)

    assert calls == 3
    assert sleeps == [40.0, 60.0]


@pytest.mark.asyncio
async def test_generate_ollama_ndjson_stream_with_terminal_marker() -> None:
    route = ModelRoute(
        name="ollama",
        provider="ollama",
        endpoint="http://localhost:11434/api/generate",
        model="deepseek-r1:7b",
        timeout_seconds=10,
    )

    body = (
        '{"response": "Hel", "done": false}\n'
        '{"response": "lo", "done": false}\n'
        '{"done": true}\n'
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/x-ndjson"},
            text=body,
        )

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )
    response = await client.generate("hello", route=route, metadata={}, stream=True)
    assert response.content == "Hello"


@pytest.mark.asyncio
async def test_generate_openai_sse_accumulates_deltas_and_ignores_done() -> None:
    route = ModelRoute(
        name="openai",
        provider="openai",
        endpoint="https://api.openai.com/v1/chat/completions",
        model="gpt-4o-mini",
        timeout_seconds=10,
    )
    body = "\n".join(
        (
            "data: malformed-json",
            'data: {"choices": "malformed"}',
            'data: {"choices": [{"delta": {"content": "Hel"}}]}',
            'data: {"choices": [{"delta": {"content": "lo"}}]}',
            "data: [DONE]",
        )
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=body)

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )

    response = await client.generate("hello", route=route, stream=True)

    assert response.content == "Hello"


@pytest.mark.asyncio
async def test_generate_anthropic_sse_accumulates_text_deltas() -> None:
    route = ModelRoute(
        name="anthropic",
        provider="anthropic",
        endpoint="https://api.anthropic.com/v1/messages",
        model="claude-test",
        timeout_seconds=10,
    )
    body = "\n".join(
        (
            "event: content_block_delta",
            'data: {"type": "content_block_delta", "delta": '
            '{"type": "text_delta", "text": "Hel"}}',
            "event: content_block_delta",
            'data: {"type": "content_block_delta", "delta": '
            '{"type": "text_delta", "text": "lo"}}',
            "event: message_stop",
            'data: {"type": "message_stop"}',
        )
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=body)

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )

    response = await client.generate("hello", route=route, stream=True)

    assert response.content == "Hello"


@pytest.mark.asyncio
async def test_ollama_midstream_error_is_sanitized() -> None:
    route = ModelRoute(
        name="ollama",
        provider="ollama",
        endpoint="http://localhost:11434/api/generate",
        model="deepseek-r1:7b",
        timeout_seconds=10,
    )
    body = '{"response": "partial"}\n{"error": "sensitive provider detail"}\n'

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/x-ndjson"},
            text=body,
        )

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )

    with pytest.raises(PlannerError) as error:
        await client.generate("hello", route=route, stream=True)

    assert "reported an error during streaming" in str(error.value)
    assert "sensitive provider detail" not in str(error.value)


@pytest.mark.asyncio
async def test_successful_empty_response_fails_clearly() -> None:
    route = ModelRoute(
        name="openai",
        provider="openai",
        endpoint="https://api.openai.com/v1/chat/completions",
        model="gpt-4o-mini",
        timeout_seconds=10,
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        _base_config(),
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )

    with pytest.raises(PlannerError, match="no usable content"):
        await client.generate("hello", route=route, stream=False)


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


@pytest.mark.asyncio
async def test_critic_uses_explicit_provider_for_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRITIC_TEST_KEY", "critic-secret")
    config = _base_config()
    config.critics = (
        CriticConfig(
            name="display-name-does-not-identify-provider",
            endpoint="https://critic.test/generate",
            api_key_env="CRITIC_TEST_KEY",
            enabled=True,
            provider="gemini",
        ),
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-goog-api-key"] == "critic-secret"
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"status": "pass"})

    transport = httpx.MockTransport(handler)
    client = PlannerClient(
        config,
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )

    outcome = await client.run_critics({"summary": "safe"})

    assert outcome.accepted is True
