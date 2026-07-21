"""Workspace snapshot and restore management."""

from __future__ import annotations

import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from aurora.paths import require_within, resolve_within


@dataclass(slots=True)
class WorkspaceSnapshot:
    """Metadata about a stored workspace snapshot."""

    tag: str
    archive_path: Path
    created_at: str
    size_bytes: int


class WorkspaceManager:
    """Create and restore workspace snapshots for reproducibility."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or Path("artifacts/workspace")
        self._root.mkdir(parents=True, exist_ok=True)

    def snapshot(self, tag: str | None = None, include: Iterable[Path] | None = None) -> WorkspaceSnapshot:
        """Create a tar archive snapshot of the current workspace."""

        tag = tag or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = resolve_within(self._root, f"{tag}.tar.gz", label="snapshot tag")
        include_paths: List[Path]
        if include:
            include_paths = [require_within(Path.cwd(), Path(p), label="snapshot input") for p in include]
        else:
            include_paths = [Path.cwd()]

        with tarfile.open(archive, mode="w:gz") as tar:
            for path in include_paths:
                arcname = path.name if path == Path.cwd() else path.relative_to(path.parent)
                tar.add(path, arcname=arcname)
        created_at = datetime.now(timezone.utc).isoformat()
        size_bytes = archive.stat().st_size
        return WorkspaceSnapshot(tag=tag, archive_path=archive, created_at=created_at, size_bytes=size_bytes)

    def restore(self, tag: str, destination: Path | None = None) -> Path:
        """Restore a snapshot into the destination directory."""

        archive = resolve_within(self._root, f"{tag}.tar.gz", label="snapshot tag")
        if not archive.exists():
            raise FileNotFoundError(f"Snapshot '{tag}' not found at {archive}")
        destination = (destination or Path.cwd()).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive, mode="r:gz") as tar:
            members = tar.getmembers()
            for member in members:
                if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                    raise ValueError(f"Unsupported archive member: {member.name}")
                resolve_within(destination, member.name, label="archive member")
            tar.extractall(destination, members=members)
        return destination

    def delete(self, tag: str) -> None:
        """Remove a stored snapshot."""

        archive = resolve_within(self._root, f"{tag}.tar.gz", label="snapshot tag")
        if archive.exists():
            archive.unlink()

    def list(self) -> list[WorkspaceSnapshot]:
        """List available snapshots with metadata."""

        snapshots: list[WorkspaceSnapshot] = []
        for archive in sorted(self._root.glob("*.tar.gz")):
            created_at = datetime.fromtimestamp(archive.stat().st_mtime, timezone.utc).isoformat()
            snapshots.append(
                WorkspaceSnapshot(
                    tag=archive.stem.replace(".tar", ""),
                    archive_path=archive,
                    created_at=created_at,
                    size_bytes=archive.stat().st_size,
                )
            )
        return snapshots

    def status(self) -> dict[str, str | int | None]:
        """Return quick status information about snapshots."""

        snapshots = self.list()
        total_size = sum(s.size_bytes for s in snapshots)
        return {
            "count": len(snapshots),
            "total_size_bytes": total_size,
            "latest": snapshots[-1].tag if snapshots else None,
        }
