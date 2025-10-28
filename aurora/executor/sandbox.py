"""Sandbox runners for executing commands."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from aurora.telemetry.errors import ErrorLogger

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str


class SandboxError(RuntimeError):
    """Raised when sandbox execution fails."""


class SandboxRunner:
    def run(
        self,
        command: Sequence[str],
        workdir: Path | None = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        raise NotImplementedError


@dataclass(slots=True)
class LocalSandbox(SandboxRunner):
    env: dict[str, str] | None = None

    def run(
        self,
        command: Sequence[str],
        workdir: Path | None = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        merged_env = dict(self.env or {})
        if env:
            merged_env.update(env)
        result = subprocess.run(
            command,
            cwd=workdir,
            env=merged_env or None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise SandboxError(result.stderr or result.stdout)
        return SandboxResult(result.returncode, result.stdout, result.stderr)


@dataclass(slots=True)
class SandboxMount:
    source: Path
    target: str
    read_only: bool = True

    def to_docker_flag(self) -> str:
        mode = "ro" if self.read_only else "rw"
        return f"{self.source}:{self.target}:{mode}"


@dataclass(slots=True)
class DockerSandbox(SandboxRunner):
    image: str
    mounts: Sequence[SandboxMount]
    env: dict[str, str] | None = None
    network: str | None = None
    seccomp_profile: Path | None = None
    apparmor_profile: str | None = None
    cpu_limit: float | None = None
    memory_limit: str | None = None
    read_only_root: bool = True
    additional_args: Sequence[str] = ()

    def run(
        self,
        command: Sequence[str],
        workdir: Path | None = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        docker_bin = shutil.which("docker")
        if not docker_bin:
            raise SandboxError("docker binary is not available on PATH")
        docker_command: list[str] = [
            docker_bin,
            "run",
            "--rm",
        ]
        if self.read_only_root:
            docker_command.append("--read-only")
        for mount in self.mounts:
            docker_command.extend(["-v", mount.to_docker_flag()])
        merged_env = dict(self.env or {})
        if env:
            merged_env.update(env)
        for key, value in merged_env.items():
            docker_command.extend(["-e", f"{key}={value}"])
        if self.network:
            docker_command.extend(["--network", self.network])
        if self.seccomp_profile:
            docker_command.extend(["--security-opt", f"seccomp={self.seccomp_profile}"])
        if self.apparmor_profile:
            docker_command.extend(["--security-opt", f"apparmor={self.apparmor_profile}"])
        if self.cpu_limit:
            docker_command.extend(["--cpus", str(self.cpu_limit)])
        if self.memory_limit:
            docker_command.extend(["--memory", self.memory_limit])
        docker_command.extend(self.additional_args)
        docker_command.append(self.image)
        docker_command.extend(command)
        result = subprocess.run(
            docker_command,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise SandboxError(result.stderr or result.stdout)
        return SandboxResult(result.returncode, result.stdout, result.stderr)


@dataclass(slots=True)
class FirecrackerResources:
    vcpu_count: int = 2
    memory_mib: int = 1024
    jailer_user: int = 1000
    jailer_group: int = 1000


@dataclass(slots=True)
class FirecrackerNetwork:
    tap_device: str
    mac_address: str = "AA:FC:00:00:00:01"


@dataclass(slots=True)
class FirecrackerSandbox(SandboxRunner):
    kernel_image: Path
    rootfs_image: Path
    workspace: Path
    resources: FirecrackerResources = FirecrackerResources()
    network: FirecrackerNetwork | None = None
    egress_allowed: bool = False
    firecracker_bin: str = "firecracker"
    firectl_bin: str = "firectl"
    snapshot_dir: Path | None = None
    error_logger: ErrorLogger | None = None

    def run(
        self,
        command: Sequence[str],
        workdir: Path | None = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        if not shutil.which(self.firectl_bin):
            raise SandboxError("firectl binary is not available; cannot launch Firecracker VM")
        if not self.kernel_image.exists():
            raise SandboxError(f"Kernel image {self.kernel_image} not found")
        if not self.rootfs_image.exists():
            raise SandboxError(f"Rootfs image {self.rootfs_image} not found")

        vm_id = f"aurora-{uuid.uuid4().hex[:10]}"
        with tempfile.TemporaryDirectory(prefix=f"{vm_id}-", dir=self.snapshot_dir or self.workspace) as tempdir:
            temp_path = Path(tempdir)
            rootfs_path = temp_path / "rootfs.ext4"
            shutil.copy2(self.rootfs_image, rootfs_path)

            metadata = {
                "aurora": {
                    "command": list(command),
                    "timestamp": time.time(),
                    "workspace": str(workdir or self.workspace),
                }
            }
            metadata_path = temp_path / "metadata.json"
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

            firectl_command: list[str] = [
                self.firectl_bin,
                "--kernel",
                str(self.kernel_image),
                "--root-drive",
                str(rootfs_path),
                "--firecracker-binary",
                self.firecracker_bin,
                "--vcpu-count",
                str(self.resources.vcpu_count),
                "--memory",
                str(self.resources.memory_mib),
                "--metadata",
                str(metadata_path),
                "--exec-file",
                "/sbin/init",
                "--log-level",
                "Warn",
            ]
            if not self.egress_allowed:
                LOGGER.debug("Firecracker sandbox running without network egress")
            elif self.network:
                firectl_command.extend(
                    [
                        "--tap-device",
                        f"{self.network.tap_device}/{self.network.mac_address}",
                    ]
                )
            else:
                LOGGER.warning("Firecracker sandbox requested egress but no network config supplied")
            result = subprocess.run(
                firectl_command,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                self._log_failure(result, vm_id)
                raise SandboxError(result.stderr or result.stdout)
        return SandboxResult(0, result.stdout if 'result' in locals() else "", result.stderr if 'result' in locals() else "")

    def _log_failure(self, result: subprocess.CompletedProcess[str], vm_id: str) -> None:
        if self.error_logger:
            self.error_logger.log(
                "firecracker_failure",
                f"Firecracker VM {vm_id} failed",
                {"stdout": result.stdout, "stderr": result.stderr},
            )
        LOGGER.error(
            "Firecracker sandbox failed: %s",
            result.stderr or result.stdout,
            extra={"vm_id": vm_id},
        )


def build_mounts(entries: Iterable[dict[str, object]]) -> list[SandboxMount]:
    mounts: list[SandboxMount] = []
    for entry in entries:
        source = Path(str(entry["source"]))
        target = str(entry["target"])
        read_only = bool(entry.get("readonly", True))
        mounts.append(SandboxMount(source=source, target=target, read_only=read_only))
    return mounts
