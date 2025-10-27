"""Planner client for interacting with model providers and critics."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from .config import CriticConfig, CriticStrategy, ModelRoute, PlannerConfig
from .secret import build_redactor

LOGGER = logging.getLogger(__name__)

PASS_STATUSES = {"pass", "approved", "ok", "success"}


class PlannerError(Exception):
    """Raised when planner encounters an unrecoverable error."""


@dataclass(slots=True)
class PlannerResponse:
    content: str
    redacted: bool
    route: str
    provider: str


@dataclass(slots=True)
class CriticOutcome:
    accepted: bool
    reasons: list[str]
    results: list[dict[str, Any]]


class PlannerClient:
    def __init__(
        self,
        config: PlannerConfig,
        client_factory: Callable[..., httpx.AsyncClient] | None = None,
    ) -> None:
        self._config = config
        self._client_factory = client_factory or (lambda **kwargs: httpx.AsyncClient(**kwargs))
        self._redactor = (
            build_redactor(config.secret_redaction.patterns)
            if config.secret_redaction.enabled
            else None
        )

    async def generate(
        self,
        prompt: str,
        route: ModelRoute,
        metadata: dict[str, Any] | None = None,
        stream: bool = True,
    ) -> PlannerResponse:
        payload = self._build_payload(route, prompt, metadata or {}, stream)
        headers = self._build_headers(route)
        timeout = route.timeout_seconds or self._config.primary.timeout_seconds
        attempts = self._config.retry_policy.max_attempts
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                async with self._client_factory(timeout=timeout) as client:
                    response = await client.post(route.endpoint, json=payload, headers=headers)
                if response.status_code >= 500:
                    raise PlannerError(f"Provider error {response.status_code}")
                content = await self._parse_response(response, route.provider, stream=stream)
                redacted_content, redacted = self.redact_text(content)
                return PlannerResponse(
                    content=redacted_content,
                    redacted=redacted,
                    route=route.name,
                    provider=route.provider,
                )
            except Exception as exc:  # pragma: no cover - retries tested separately
                last_exc = exc
                if attempt + 1 >= attempts:
                    break
                backoff = self._config.retry_policy.backoff_seconds * (2 ** attempt)
                await asyncio.sleep(backoff)
        raise PlannerError(f"Planner request failed: {last_exc}") from last_exc

    async def run_critics(self, payload: dict[str, Any]) -> CriticOutcome:
        results: list[dict[str, Any]] = []
        for critic in self._config.critics:
            if not critic.enabled:
                continue
            record = await self._call_critic(critic, payload)
            results.append(record)
        if not results:
            return CriticOutcome(True, [], [])
        return self._aggregate_critics(results)

    def redact_text(self, text: str) -> tuple[str, bool]:
        if not self._redactor:
            return text, False
        return self._redactor.redact(text)

    def _build_payload(
        self,
        route: ModelRoute,
        prompt: str,
        metadata: dict[str, Any],
        stream: bool,
    ) -> dict[str, Any]:
        provider = route.provider.lower()
        if provider == "openai":
            payload = {
                "model": route.model,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "stream": stream,
            }
        elif provider == "anthropic":
            payload = {
                "model": route.model,
                "max_tokens": route.max_output_tokens or 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
            }
            payload.update(route.extra or {})
        elif provider in {"google", "gemini"}:
            payload = {
                "model": route.model,
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ],
            }
        else:  # default to Ollama-compatible payload
            payload = {
                "model": route.model,
                "prompt": prompt,
                "options": {"stream": stream},
            }
        if metadata:
            payload.setdefault("metadata", metadata)
        return payload

    def _build_headers(self, route: ModelRoute) -> dict[str, str]:
        headers: dict[str, str] = {}
        if route.api_key_env:
            api_key = os.getenv(route.api_key_env)
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def _parse_response(self, response: httpx.Response, provider: str, stream: bool) -> str:
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            text = response.text
            return self._parse_stream(text, provider)
        if "application/json" in content_type or response.text.startswith("{"):
            data = response.json()
        else:
            data = {"response": response.text}
        return self._extract_content(data, provider)

    def _parse_stream(self, text: str, provider: str) -> str:
        parts: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            chunk = self._extract_content(payload, provider)
            if chunk:
                parts.append(chunk)
        return "".join(parts)

    def _extract_content(self, data: dict[str, Any], provider: str) -> str:
        provider = provider.lower()
        if provider == "openai":
            choices = data.get("choices") or []
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "") or ""
        if provider == "anthropic":
            content = data.get("content") or []
            if isinstance(content, list):
                return "".join(block.get("text", "") for block in content)
            return str(content)
        if provider in {"google", "gemini"}:
            candidates = data.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(part.get("text", "") for part in parts)
        return (
            data.get("response")
            or data.get("output")
            or data.get("output_text")
            or data.get("content", "")
        )

    async def _call_critic(self, critic: CriticConfig, payload: dict[str, Any]) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if critic.api_key_env:
            api_key = os.getenv(critic.api_key_env)
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        async with self._client_factory(timeout=self._config.primary.timeout_seconds) as client:
            response = await client.post(critic.endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return {
            "critic": critic.name,
            "response": response.json(),
        }

    def _aggregate_critics(self, results: list[dict[str, Any]]) -> CriticOutcome:
        strategy: CriticStrategy = self._config.critic_strategy or CriticStrategy()
        statuses = {
            record["critic"]: str(record.get("response", {}).get("status", "unknown")).lower()
            for record in results
        }
        pass_count = sum(status in PASS_STATUSES for status in statuses.values())
        reasons: list[str] = []
        accepted = True

        if strategy.mode == "all":
            accepted = pass_count == len(statuses)
        elif strategy.mode == "any":
            accepted = pass_count > 0
        elif strategy.mode == "priority" and strategy.priority:
            for name in strategy.priority:
                status = statuses.get(name)
                if status and status not in PASS_STATUSES:
                    accepted = False
                    reasons.append(f"Critic {name} returned {status}")
                    break
        elif strategy.mode == "quorum" and strategy.threshold:
            accepted = pass_count >= strategy.threshold
        else:
            accepted = pass_count == len(statuses)

        if not accepted and not reasons:
            for critic, status in statuses.items():
                if status not in PASS_STATUSES:
                    reasons.append(f"Critic {critic} returned {status}")

        return CriticOutcome(accepted=accepted, reasons=reasons, results=results)

