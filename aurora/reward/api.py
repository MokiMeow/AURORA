"""Public API for consuming reward history."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any, List


class RewardAPI:
    def __init__(self, history_path: Path) -> None:
        self._history_path = history_path

    def latest(self) -> dict[str, Any] | None:
        entries = self.history(limit=1)
        return entries[0] if entries else None

    def history(self, limit: int = 20) -> List[dict[str, Any]]:
        if not self._history_path.exists():
            return []
        lines = self._history_path.read_text(encoding="utf-8").splitlines()
        records: List[dict[str, Any]] = []
        for line in lines[-limit:]:
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        records.reverse()
        return records

    def summary(self, limit: int = 50) -> dict[str, Any]:
        records = self.history(limit=limit)
        if not records:
            return {"count": 0, "average_reward": 0.0, "success_rate": 0.0}
        rewards = [record.get("reward", 0.0) for record in records]
        successes = [record.get("success", False) for record in records]
        return {
            "count": len(records),
            "average_reward": mean(rewards),
            "success_rate": sum(1 for s in successes if s) / len(successes),
        }


__all__ = ["RewardAPI"]
