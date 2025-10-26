"""Executor service for applying self-edits within sandboxed environments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class SandboxRunner(Protocol):
    def run(self, command: list[str], workdir: Path | None = None) -> int:  # pragma: no cover
        """Execute a command within the sandbox and return exit code."""


@dataclass(slots=True)
class ExecutionConfig:
    sandbox: SandboxRunner
    profile: str
    workspace: Path


class ExecutorService:
    def __init__(self, config: ExecutionConfig) -> None:
        self._config = config

    def apply(self, edit_path: Path) -> None:
        if not edit_path.exists():
            msg = f"Edit file {edit_path} does not exist"
            raise FileNotFoundError(msg)
        # TODO: integrate patch application, CI orchestration, reward calculation.
        # Placeholder call to sandbox runner to demonstrate interface.
        self._config.sandbox.run(["echo", "Applying self-edit"], workdir=self._config.workspace)

