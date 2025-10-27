"""Planner client for interacting with Ollama and critic models."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from .config import CriticConfig, PlannerConfig
from .secret import build_redactor

LOGGER = logging.getLogger(__name__)


class PlannerError(Exception):
    """Raised when planner encounters an unrecoverable error."""


@dataclass(slots=True)
class PlannerResponse:
    content: str
    redacted: bool


class PlannerClient:
    def __init__(self, config: PlannerConfig) -> None:
        self._config = config
        self._redactor = (
            build_redactor(config.secret_redaction.patterns)
            if config.secret_redaction.enabled
            else None
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(5),
        reraise=True,
    )
    async def generate(self, prompt: str) -> PlannerResponse:
        payload = {
            "model": self._config.primary.model,
            "prompt": prompt,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self._config.primary.timeout_seconds) as client:
            response = await client.post(self._config.primary.endpoint, json=payload)
        response.raise_for_status()
        data = response.json()
        content = data.get("response") or data.get("output")
        if not content:
            raise PlannerError("Planner response missing content")
        if self._redactor:
            content, redacted = self._redactor.redact(content)
        else:
            redacted = False
        return PlannerResponse(content=content, redacted=redacted)

    async def run_critics(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for critic in self._config.critics:
            if not critic.enabled:
                continue
            record = await self._call_critic(critic, payload)
            results.append(record)
        return results

    async def _call_critic(self, critic: CriticConfig, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {}
        if critic.api_key_env:
            api_key = os.getenv(critic.api_key_env)
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        async with httpx.AsyncClient(timeout=self._config.primary.timeout_seconds) as client:
            response = await client.post(critic.endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return {
            "critic": critic.name,
            "response": response.json(),
        }

