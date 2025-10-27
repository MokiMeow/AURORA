"""Executor configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Dict, List


@dataclass(slots=True)
class CIPipelineStep:
    name: str
    command: list[str]
    fail_fast: bool | None = None


@dataclass(slots=True)
class CIProfile:
    name: str
    steps: tuple[CIPipelineStep, ...]
    timeout_minutes: int
    fail_fast: bool


@dataclass(slots=True)
class ExecutorConfig:
    workspace: Path
    profiles: dict[str, CIProfile]
    sandbox: str
    artifacts_dir: Path
    policy_path: Path | None = None
    docker_image: str | None = None
    docker_env: Dict[str, str] | None = None
    docker_mounts: List[dict] | None = None

