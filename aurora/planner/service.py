"""Planner service orchestrates LLM calls and schema validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from .schema import SelfEdit


@dataclass(slots=True)
class PlannerConfig:
    endpoint: str
    model: str
    critic_endpoints: list[str]
    timeout_seconds: float = 120.0


class PlannerService:
    def __init__(self, config: PlannerConfig) -> None:
        self._config = config

    async def generate_self_edit(self, task: str, auto: bool, critic: bool) -> SelfEdit:
        payload = {
            "model": self._config.model,
            "prompt": task,
            "options": {"temperature": 0.2, "top_p": 0.95},
        }
        async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
            response = await client.post(self._config.endpoint, json=payload)
        response.raise_for_status()
        data = self._parse_response(response.json())
        self_edit = self._validate_self_edit(data)
        if critic and self._config.critic_endpoints:
            await self._run_critics(self_edit)
        return self_edit

    def _parse_response(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict) and "output" in data:
            try:
                return json.loads(data["output"])
            except json.JSONDecodeError as exc:
                msg = "Planner response is not valid JSON"
                raise ValueError(msg) from exc
        if isinstance(data, dict):
            return data
        msg = "Unexpected planner response structure"
        raise ValueError(msg)

    def _validate_self_edit(self, payload: dict[str, Any]) -> SelfEdit:
        try:
            return SelfEdit.model_validate(payload)
        except ValidationError as exc:
            error_path = Path("artifacts") / "latest_planner_error.json"
            error_path.parent.mkdir(parents=True, exist_ok=True)
            error_path.write_text(exc.json())
            raise

    async def _run_critics(self, self_edit: SelfEdit) -> None:
        critique_payload = json.loads(self_edit.model_dump_json(indent=2))
        for endpoint in self._config.critic_endpoints:
            async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
                response = await client.post(endpoint, json=critique_payload)
            response.raise_for_status()

