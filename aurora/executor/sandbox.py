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


@dataclass(slots=True)
class DockerSandbox(SandboxRunner):
    image: str
    mounts: Sequence[dict]
    env: dict[str, str] | None = None

    def run(self, command: Sequence[str], workdir: Path | None = None) -> int:
        docker_command = [
            "docker",
            "run",
            "--rm",
        ]
        for mount in self.mounts:
            docker_command.extend(["-v", f"{mount['source']}:{mount['target']}:{mount.get('mode', 'rw')}" ])
        if self.env:
            for key, value in self.env.items():
                docker_command.extend(["-e", f"{key}={value}"])
        docker_command.extend([self.image])
        docker_command.extend(command)
        result = subprocess.run(docker_command, cwd=workdir, capture_output=True, text=True)
        if result.returncode != 0:
            raise SandboxError(result.stderr)
        return result.returncode

