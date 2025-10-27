"""Policy evaluation for executor acceptance gates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class PolicyResult:
    accepted: bool
    reasons: list[str]


class PolicyEvaluator:
    def __init__(self, policy_path: Path | None) -> None:
        self._policy_path = policy_path
        self._policy = self._load_policy()

    def evaluate(self, ci_results: list[dict]) -> PolicyResult:
        reasons: list[str] = []
        accepted = True
        for result in ci_results:
            if not result["success"]:
                accepted = False
                reasons.append(f"CI step failed: {result['step']}")
        if accepted and self._policy:
            for rule in self._policy.get("required_steps", []):
                if not any(rule in result["step"] and result["success"] for result in ci_results):
                    accepted = False
                    reasons.append(f"Required step missing: {rule}")
        return PolicyResult(accepted=accepted, reasons=reasons)

    def _load_policy(self) -> dict[str, Any] | None:
        if not self._policy_path or not self._policy_path.exists():
            return None
        text = self._policy_path.read_text(encoding="utf-8").strip()
        if not text:
            return {}
        suffix = self._policy_path.suffix.lower()
        if suffix in {".yaml", ".yml"}:
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
        return data or {}

