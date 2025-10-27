"""Executor configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Sequence


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
class FirecrackerConfig:
    kernel_image: Path
    rootfs_image: Path
    resources: dict | None = None
    network: dict | None = None
    snapshot_dir: Path | None = None
    firecracker_bin: str = "firecracker"
    firectl_bin: str = "firectl"


@dataclass(slots=True)
class SandboxPolicies:
    egress_allowed: bool
    storage_mounts: list[dict]
    allowlist: list[str] | None = None


@dataclass(slots=True)
class DockerConfig:
    image: str
    mounts: list[dict]
    env: Dict[str, str] | None = None
    network: str | None = None
    seccomp_profile: Path | None = None
    apparmor_profile: str | None = None
    cpu_limit: float | None = None
    memory_limit: str | None = None
    read_only_root: bool = True
    additional_args: Sequence[str] | None = None


@dataclass(slots=True)
class ExecutorConfig:
    workspace: Path
    profiles: dict[str, CIProfile]
    sandbox: str
    artifacts_dir: Path
    policy_path: Path | None = None
    docker: DockerConfig | None = None
    firecracker_config: FirecrackerConfig | None = None
    sandbox_policies: SandboxPolicies | None = None
