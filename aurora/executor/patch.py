"""Utilities for applying and validating diff patches."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class PatchError(RuntimeError):
    """Raised when patch operations fail."""


def dry_run(patch: str, workspace: Path) -> None:
    """Validate a patch can be applied cleanly."""

    result = subprocess.run(
        ["git", "apply", "--check", "-"],
        input=patch.encode("utf-8"),
        cwd=workspace,
        capture_output=True,
    )
    if result.returncode != 0:
        raise PatchError(result.stderr.decode("utf-8"))


def apply(patch: str, workspace: Path) -> None:
    """Apply patch to workspace."""

    result = subprocess.run(
        ["git", "apply", "-"],
        input=patch.encode("utf-8"),
        cwd=workspace,
        capture_output=True,
    )
    if result.returncode != 0:
        raise PatchError(result.stderr.decode("utf-8"))


def apply_three_way(patch: str, workspace: Path) -> None:
    """Attempt to apply patch using three-way merge fallback."""

    result = subprocess.run(
        ["git", "apply", "--3way", "-"],
        input=patch.encode("utf-8"),
        cwd=workspace,
        capture_output=True,
    )
    if result.returncode != 0:
        raise PatchError(result.stderr.decode("utf-8"))


def rollback(patch: str, workspace: Path) -> None:
    """Revert applied patch."""

    subprocess.run(
        ["git", "apply", "-R", "-"],
        input=patch.encode("utf-8"),
        cwd=workspace,
        capture_output=True,
    )


def diff_summary(workspace: Path) -> str:
    """Return summary of current diff against HEAD."""

    result = subprocess.run(
        ["git", "diff", "--stat"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def detect_test_deletions(patch: str) -> list[str]:
    """Detect removed test files or lines in diff."""

    deletions: list[str] = []
    current_file = ""
    for line in patch.splitlines():
        if line.startswith("--- a/"):
            current_file = line[6:]
        elif line.startswith("--- "):
            current_file = ""
        if current_file.startswith("tests/") and line.startswith("-") and not line.startswith("---"):
            deletions.append(current_file)
    return deletions

