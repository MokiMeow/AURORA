"""PDCA telemetry helpers for planner."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PDCA_LOG = Path("telemetry/pdca.jsonl")
PDCA_LOG.parent.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class PDCAEntry:
    phase: str
    event: str
    payload: dict[str, Any]

    def write(self) -> None:
        record = {
            "phase": self.phase,
            "event": self.event,
            "payload": self.payload,
        }
        with PDCA_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

