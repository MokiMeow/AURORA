"""Sandbox runners for executing commands."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


class SandboxError(RuntimeError):
    """Raised when sandbox execution fails."""


class SandboxRunner:
    def run(self, command: Sequence[str], workdir: Path | None = None) -> int:
        raise NotImplementedError


@dataclass(slots=True)
class LocalSandbox(SandboxRunner):
    env: dict[str, str] | None = None

    def run(self, command: Sequence[str], workdir: Path | None = None) -> int:
        result = subprocess.run(command, cwd=workdir, env=self.env, capture_output=True, text=True)
        if result.returncode != 0:
            raise SandboxError(result.stderr)
        return result.returncode

