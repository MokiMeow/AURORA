"""Tests for session manager."""

import json
from pathlib import Path

from aurora.session import SessionManager


def test_session_start_resume_archive(tmp_path: Path) -> None:
    manager = SessionManager(tmp_path)
    session = manager.start("demo", "desc", metadata={"ticket": "JIRA-1"})
    assert session.path.exists()
    loaded = manager.resume(session.id)
    assert loaded.metadata["metadata"]["ticket"] == "JIRA-1"
    archived = manager.archive(session.id, reason="completed")
    data = json.loads(archived.metadata_path.read_text(encoding="utf-8"))
    assert data["status"] == "archived"
    assert data["archive_reason"] == "completed"


def test_session_list(tmp_path: Path) -> None:
    manager = SessionManager(tmp_path)
    manager.start("first")
    sessions = list(manager.list())
    assert len(sessions) == 1
