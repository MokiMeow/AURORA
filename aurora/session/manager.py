"""Workspace session manager."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable


@dataclass(slots=True)
class Session:
    id: str
    name: str
    path: Path
    status: str
    metadata: Dict[str, Any]

    @property
    def metadata_path(self) -> Path:
        return self.path / "metadata.json"


class SessionManager:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or Path("artifacts/sessions")
        self._root.mkdir(parents=True, exist_ok=True)

    def start(self, name: str, description: str = "", metadata: Dict[str, Any] | None = None) -> Session:
        session_id = uuid.uuid4().hex[:8]
        path = self._root / session_id
        path.mkdir(parents=True, exist_ok=True)
        payload = {
            "id": session_id,
            "name": name,
            "description": description,
            "created_at": self._ts(),
            "last_accessed": self._ts(),
            "status": "active",
            "workspace_snapshot": self._snapshot_state(),
            "metadata": metadata or {},
        }
        (path / "metadata.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return Session(id=session_id, name=name, path=path, status="active", metadata=payload)

    def resume(self, session_id: str) -> Session:
        session = self._load(session_id)
        session.metadata["last_accessed"] = self._ts()
        self._write(session)
        return session

    def archive(self, session_id: str, reason: str | None = None) -> Session:
        session = self._load(session_id)
        session.status = "archived"
        session.metadata["status"] = "archived"
        session.metadata["archived_at"] = self._ts()
        if reason:
            session.metadata.setdefault("archive_reason", reason)
        self._write(session)
        return session

    def list(self) -> Iterable[Session]:
        for metadata_file in self._root.glob("*/metadata.json"):
            data = json.loads(metadata_file.read_text(encoding="utf-8"))
            session_id = data.get("id") or metadata_file.parent.name
            yield Session(
                id=session_id,
                name=data.get("name", session_id),
                path=metadata_file.parent,
                status=data.get("status", "active"),
                metadata=data,
            )

    def _load(self, session_id: str) -> Session:
        metadata_path = self._root / session_id / "metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Session {session_id} not found")
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        return Session(
            id=session_id,
            name=data.get("name", session_id),
            path=metadata_path.parent,
            status=data.get("status", "active"),
            metadata=data,
        )

    def _write(self, session: Session) -> None:
        session.metadata_path.write_text(json.dumps(session.metadata, indent=2), encoding="utf-8")

    @staticmethod
    def _ts() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _snapshot_state(self) -> Dict[str, Any]:
        snapshot = {
            "cwd": str(Path.cwd()),
        }
        git_head = self._git_head()
        if git_head:
            snapshot["git_head"] = git_head
        return snapshot

    @staticmethod
    def _git_head() -> str | None:
        head_path = Path(".git/HEAD")
        if head_path.exists():
            try:
                return head_path.read_text(encoding="utf-8").strip()
            except OSError:
                return None
        return None
