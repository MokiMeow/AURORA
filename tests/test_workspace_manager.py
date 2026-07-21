"""Tests for workspace snapshot containment."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from aurora.workspace import WorkspaceManager


def test_snapshot_tag_cannot_escape_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    manager = WorkspaceManager(tmp_path / "snapshots")
    with pytest.raises(ValueError, match="snapshot tag"):
        manager.snapshot("../outside")


def test_restore_rejects_escaping_archive_member(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshots"
    snapshot_root.mkdir()
    archive_path = snapshot_root / "unsafe.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        payload = b"outside"
        member = tarfile.TarInfo("../outside.txt")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))

    manager = WorkspaceManager(snapshot_root)
    with pytest.raises(ValueError, match="archive member"):
        manager.restore("unsafe", tmp_path / "restore")
    assert not (tmp_path / "outside.txt").exists()
