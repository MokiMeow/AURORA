"""Local API service lifecycle management."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class APIServerState:
    status: str
    port: int | None
    started_at: str | None


class APIService:
    """Persist API server state; external process manager handles actual runtime."""

    def __init__(self, state_path: Path | None = None) -> None:
        self._path = state_path or Path("artifacts/api/server.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def start(self, port: int) -> APIServerState:
        state = APIServerState(status="running", port=port, started_at=self._timestamp())
        self._write(state)
        return state

    def stop(self) -> APIServerState:
        state = APIServerState(status="stopped", port=None, started_at=None)
        self._write(state)
        return state

    def status(self) -> APIServerState:
        if not self._path.exists():
            return APIServerState(status="stopped", port=None, started_at=None)
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return APIServerState(
            status=payload.get("status", "unknown"),
            port=payload.get("port"),
            started_at=payload.get("started_at"),
        )

    def _write(self, state: APIServerState) -> None:
        payload = {
            "status": state.status,
            "port": state.port,
            "started_at": state.started_at,
            "updated_at": self._timestamp(),
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()
