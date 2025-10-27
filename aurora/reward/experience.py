"""Experience vault logging for reward outcomes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ExperienceRecord:
    path: str
    reward: float
    success: bool
    metadata: dict[str, Any]


class ExperienceLogger:
    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: ExperienceRecord) -> None:
        entry = {
            "path": record.path,
            "reward": record.reward,
            "success": record.success,
            "metadata": record.metadata,
        }
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

