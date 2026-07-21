"""PDCA event persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PDCA_LOG = Path("telemetry/pdca.jsonl")


def PDCAEntry(phase: str, event: str, payload: dict[str, Any], path: Path | None = None) -> None:
    """Append one PDCA event to the configured local JSON Lines log."""

    output = path or PDCA_LOG
    output.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "event": event,
        "payload": payload,
    }
    with output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, default=str, sort_keys=True) + "\n")


__all__ = ["PDCAEntry", "PDCA_LOG"]
