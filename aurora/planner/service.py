"""Planner service orchestrates LLM calls, context retrieval, and schema validation."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..context.experience import ExperienceVault
from ..indexer.context_builder import build_context_packer
from ..indexer.store import GraphStore
from ..indexer.embedding import EmbeddingStore
from .client import PlannerClient, PlannerResponse
from .config_loader import load_planner_config
from .schema import SelfEdit
from .pdca import PDCAEntry

LOGGER = logging.getLogger(__name__)

ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


class PlannerService:
    def __init__(
        self,
        config_path: Path,
        graph_store: GraphStore,
        embedding_store: EmbeddingStore,
        experience_vault: ExperienceVault | None = None,
    ) -> None:
        self._config_path = config_path
        self._graph_store = graph_store
        self._embedding_store = embedding_store
        self._experience_vault = experience_vault
        self._config = load_planner_config(config_path)
        self._client = PlannerClient(self._config)
        self._context_packer = build_context_packer(
            graph_store=graph_store,
            embedding_store=embedding_store,
            experience_vault=experience_vault,
            limit=20,
        )

    async def generate_self_edit(self, task: str, auto: bool, critic: bool) -> SelfEdit:
        PDCAEntry(phase="Plan", event="start", payload={"task": task, "auto": auto, "critic": critic}).write()
        context_slices = self._context_packer.build_context(task)
        context_payload = "\n".join(f"- {slice_.summary} ({slice_.path})" for slice_ in context_slices)
        prompt = self._build_prompt(task, context_payload, auto=auto)
        try:
            response = await self._client.generate(prompt)
        except Exception as exc:  # pragma: no cover
            PDCAEntry(phase="Plan", event="error", payload={"task": task, "error": str(exc)}).write()
            raise
        self._write_artifact("planner_output.txt", response.content)
        data = self._parse_response(response.content)
        self_edit = self._validate_self_edit(data)
        if critic:
            await self._run_critics(self_edit)
        self._write_artifact("self_edit.json", self_edit.model_dump_json(indent=2))
        PDCAEntry(phase="Plan", event="complete", payload={"task": task, "redacted": response.redacted}).write()
        return self_edit

    def _build_prompt(self, task: str, context: str, auto: bool) -> str:
        instructions = [
            "You are the AURORA-SE planner operating within PDCA constraints.",
            "Generate a Self-Edit JSON strictly adhering to the schema.",
            "Ensure tests are included and policy requirements met.",
        ]
        if auto:
            instructions.append("The executor will run automatically; be thorough.")
        prompt = "\n".join(instructions)
        prompt += f"\n\nTask:\n{task}\n\nContext:\n{context}"
        return prompt

    def _parse_response(self, content: str) -> dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            msg = "Planner response is not valid JSON"
            raise ValueError(msg) from exc

    def _validate_self_edit(self, payload: dict[str, Any]) -> SelfEdit:
        try:
            self_edit = SelfEdit.model_validate(payload)
        except ValidationError as exc:
            error_path = ARTIFACTS_DIR / "latest_planner_error.json"
            error_path.write_text(exc.json())
            raise
        return self_edit

    async def _run_critics(self, self_edit: SelfEdit) -> None:
        payload = json.loads(self_edit.model_dump_json(indent=2))
        results = await self._client.run_critics(payload)
        artifact_path = ARTIFACTS_DIR / "critic_outputs.json"
        artifact_path.write_text(json.dumps(results, indent=2))
        PDCAEntry(phase="Plan", event="critic", payload={"results": [r["critic"] for r in results]}).write()

    @staticmethod
    def _write_artifact(filename: str, content: str) -> None:
        path = ARTIFACTS_DIR / filename
        path.write_text(content)

