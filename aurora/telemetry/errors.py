"""Structured local error logging."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


class ErrorLogger:
    """Append structured errors to a JSON Lines file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def log(self, category: str, message: str, context: Mapping[str, Any] | None = None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "message": message,
            "context": dict(context or {}),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str, sort_keys=True) + "\n")


__all__ = ["ErrorLogger"]
