"""Shared filesystem containment helpers."""

from __future__ import annotations

from pathlib import Path


def resolve_within(root: Path, *parts: str | Path, label: str = "path") -> Path:
    """Resolve a path and require it to remain inside *root*."""

    resolved_root = root.resolve()
    candidate = resolved_root.joinpath(*parts).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label} must remain inside {resolved_root}") from exc
    return candidate


def require_within(root: Path, candidate: Path, *, label: str = "path") -> Path:
    """Require an existing or prospective path to remain inside *root*."""

    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label} must remain inside {resolved_root}") from exc
    return resolved_candidate


__all__ = ["require_within", "resolve_within"]
