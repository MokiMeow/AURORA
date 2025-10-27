"""Experience vault logging for reward outcomes."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ExperienceRecord:
    context: dict[str, Any]
    edit: dict[str, Any]
    telemetry: dict[str, Any]
    reward: float
    regret: bool


class ExperienceLogger:
    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: ExperienceRecord) -> None:
        entry = {
            "context": record.context,
            "edit": record.edit,
            "telemetry": record.telemetry,
            "reward": record.reward,
            "regret": record.regret,
        }
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def log_regret(self, context: dict, telemetry: dict, reward: float) -> None:
        self.append(
            ExperienceRecord(
                context=context,
                edit={"summary": "regret"},
                telemetry=telemetry,
                reward=reward,
                regret=True,
            )
        )

