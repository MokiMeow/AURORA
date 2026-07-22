"""Planner client for interacting with model providers and critics."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable

import httpx

from .config import CriticConfig, CriticStrategy, ModelRoute, PlannerConfig
from .secret import build_redactor

LOGGER = logging.getLogger(__name__)

PASS_STATUSES = {"pass", "approved", "ok", "success"}
DEFAULT_ANTHROPIC_API_VERSION = "2023-06-01"
MAX_RETRY_DELAY_SECONDS = 60.0
RETRYABLE_STATUS_CODES = {408, 425, 429}


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
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._config = config
        self._client_factory = client_factory or (lambda **kwargs: httpx.AsyncClient(**kwargs))
        self._sleep = sleep or asyncio.sleep
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
        attempts = max(1, self._config.retry_policy.max_attempts)
        last_error = "transport error"
        for attempt in range(attempts):
            try:
                async with self._client_factory(timeout=timeout) as client:
                    response = await client.post(route.endpoint, json=payload, headers=headers)
            except httpx.TransportError as exc:
                last_error = f"transport error ({type(exc).__name__})"
                if attempt + 1 >= attempts:
                    break
                await self._sleep(self._retry_delay(attempt))
                continue
            except Exception as exc:
                raise PlannerError(
                    f"Planner request failed for provider {route.provider}: client error"
                ) from exc

            if not 200 <= response.status_code < 300:
                error = self._http_error(route.provider, response)
                if not self._is_retryable_status(response.status_code):
                    raise error
                last_error = str(error)
                if attempt + 1 >= attempts:
                    break
                await self._sleep(self._retry_delay(attempt, response))
                continue

            content = await self._parse_response(response, route.provider, stream=stream)
            redacted_content, redacted = self.redact_text(content)
            return PlannerResponse(
                content=redacted_content,
                redacted=redacted,
                route=route.name,
                provider=route.provider,
            )
        raise PlannerError(
            f"Planner request failed for provider {route.provider} after {attempts} attempts: "
            f"{last_error}"
        )

    @staticmethod
    def _is_retryable_status(status_code: int) -> bool:
        return status_code in RETRYABLE_STATUS_CODES or status_code >= 500

    @staticmethod
    def _http_error(provider: str, response: httpx.Response) -> PlannerError:
        request_id = response.headers.get("x-request-id") or response.headers.get("request-id")
        suffix = f", request ID {request_id}" if request_id else ""
        return PlannerError(
            f"Provider {provider} request failed with status {response.status_code}{suffix}"
        )

    def _retry_delay(self, attempt: int, response: httpx.Response | None = None) -> float:
        if response is not None:
            retry_after = self._parse_retry_after(response.headers.get("retry-after"))
            if retry_after is not None:
                return retry_after
        backoff = self._config.retry_policy.backoff_seconds * (2**attempt)
        return min(MAX_RETRY_DELAY_SECONDS, max(0.0, float(backoff)))

    @staticmethod
    def _parse_retry_after(value: str | None) -> float | None:
        if not value:
            return None
        try:
            delay = float(value.strip())
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
            except (TypeError, ValueError, OverflowError):
                return None
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            delay = (retry_at - datetime.now(timezone.utc)).total_seconds()
        if not math.isfinite(delay) or delay < 0:
            return None
        return min(delay, MAX_RETRY_DELAY_SECONDS)

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
        extra = dict(route.extra or {})
        extra.pop("api_version", None)
        if provider == "openai":
            payload = {
                "model": route.model,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "stream": stream,
            }
            if metadata:
                payload["metadata"] = metadata
        elif provider == "anthropic":
            payload = {
                "model": route.model,
                "max_tokens": route.max_output_tokens or 1024,
                "stream": stream,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
            }
        elif provider in {"google", "gemini"}:
            payload = {
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
                "stream": stream,
            }
        payload.update(extra)
        return payload

    def _build_headers(self, route: ModelRoute) -> dict[str, str]:
        api_version_value = (route.extra or {}).get("api_version") or DEFAULT_ANTHROPIC_API_VERSION
        api_version = str(api_version_value)
        return self._provider_headers(route.provider, route.api_key_env, api_version=api_version)

    def _provider_headers(
        self,
        provider: str | None,
        api_key_env: str | None,
        *,
        api_version: str = DEFAULT_ANTHROPIC_API_VERSION,
    ) -> dict[str, str]:
        normalized_provider = (provider or "").lower()
        headers: dict[str, str] = {}
        if normalized_provider == "anthropic":
            headers["anthropic-version"] = api_version
        if not api_key_env:
            return headers

        api_key = os.getenv(api_key_env)
        if not api_key:
            raise PlannerError(
                f"Missing credential environment variable {api_key_env} for provider "
                f"{normalized_provider or 'configured critic'}"
            )
        if normalized_provider == "anthropic":
            headers["x-api-key"] = api_key
        elif normalized_provider in {"google", "gemini"}:
            headers["x-goog-api-key"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def _parse_response(self, response: httpx.Response, provider: str, stream: bool) -> str:
        content_type = response.headers.get("content-type", "").lower()
        if "text/event-stream" in content_type or "application/x-ndjson" in content_type:
            content = self._parse_stream(response.text, provider)
        elif "application/ndjson" in content_type:
            content = self._parse_stream(response.text, provider)
        elif "application/json" in content_type or response.text.lstrip().startswith(("{", "[")):
            try:
                data = response.json()
            except ValueError:
                data = {}
            if isinstance(data, list):
                content = "".join(
                    self._extract_content(item, provider) for item in data if isinstance(item, dict)
                )
            elif isinstance(data, dict):
                content = self._extract_content(data, provider)
            else:
                content = ""
        else:
            content = response.text
        if not content.strip():
            mode = "stream" if stream else "response"
            raise PlannerError(f"Provider {provider} returned no usable content in successful {mode}")
        return content

    def _parse_stream(self, text: str, provider: str) -> str:
        parts: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            elif line.startswith(("event:", "id:", "retry:", ":")):
                continue
            if line in {"[DONE]", "[done]"}:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            if "error" in payload or payload.get("type") == "error":
                raise PlannerError(f"Provider {provider} reported an error during streaming")
            chunk = self._extract_content(payload, provider)
            if chunk:
                parts.append(chunk)
        return "".join(parts)

    def _extract_content(self, data: dict[str, Any], provider: str) -> str:
        provider = provider.lower()
        if provider == "openai":
            choices = data.get("choices") or []
            if isinstance(choices, list) and choices and isinstance(choices[0], dict):
                choice = choices[0]
                delta = choice.get("delta") or {}
                message = choice.get("message") or {}
                delta_content = delta.get("content") if isinstance(delta, dict) else None
                message_content = message.get("content") if isinstance(message, dict) else None
                return self._text_content(delta_content or message_content)
        if provider == "anthropic":
            delta = data.get("delta") or {}
            if isinstance(delta, dict) and isinstance(delta.get("text"), str):
                return delta["text"]
            content = data.get("content") or []
            return self._text_content(content)
        if provider in {"google", "gemini"}:
            candidates = data.get("candidates") or []
            if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict):
                candidate_content = candidates[0].get("content") or {}
                parts = (
                    candidate_content.get("parts", [])
                    if isinstance(candidate_content, dict)
                    else []
                )
                return self._text_content(parts)
        return self._text_content(
            data.get("response")
            or data.get("output")
            or data.get("output_text")
            or data.get("content", "")
        )

    @staticmethod
    def _text_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                text
                for item in content
                if isinstance(item, dict)
                for text in (item.get("text"),)
                if isinstance(text, str)
            )
        return ""

    async def _call_critic(self, critic: CriticConfig, payload: dict[str, Any]) -> dict[str, Any]:
        headers = self._provider_headers(critic.provider, critic.api_key_env)
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

