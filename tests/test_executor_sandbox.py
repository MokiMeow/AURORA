"""Tests for sandbox runners."""

from pathlib import Path

import subprocess
import shutil

from aurora.executor.sandbox import (
    DockerSandbox,
    FirecrackerResources,
    FirecrackerSandbox,
    SandboxMount,
    SandboxError,
)


def test_docker_sandbox_builds_command(monkeypatch, tmp_path: Path):
    seccomp = tmp_path / "seccomp.json"
    seccomp.write_text("{}", encoding="utf-8")

    captured = {}

    def fake_run(cmd, cwd=None, capture_output=True, text=True, timeout=None):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/docker" if name == "docker" else None)

    sandbox = DockerSandbox(
        image="aurora-se/runtime:latest",
        mounts=[SandboxMount(source=tmp_path, target="/workspace", read_only=False)],
        env={"AURORA_MODE": "ci"},
        network="none",
        seccomp_profile=seccomp,
        apparmor_profile="aurora-default",
        cpu_limit=2.0,
        memory_limit="4g",
        read_only_root=True,
        additional_args=["--tmpfs", "/tmp"],
    )

    sandbox.run(["echo", "hello"], workdir=tmp_path)

    cmd = captured["cmd"]
    assert "--read-only" in cmd
    assert "--security-opt" in " ".join(cmd)
    assert "--tmpfs" in cmd
    assert "echo" in cmd


def test_firecracker_sandbox_requires_binary(monkeypatch, tmp_path: Path):
    kernel = tmp_path / "vmlinux"
    rootfs = tmp_path / "rootfs.ext4"
    kernel.write_bytes(b"kernel")
    rootfs.write_bytes(b"rootfs")

    monkeypatch.setattr(shutil, "which", lambda name: None)
    sandbox = FirecrackerSandbox(
        kernel_image=kernel,
        rootfs_image=rootfs,
        workspace=tmp_path,
        resources=FirecrackerResources(vcpu_count=1, memory_mib=256),
    )
    try:
        sandbox.run(["/bin/true"])
    except SandboxError as exc:
        assert "firectl" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("SandboxError expected")


def test_firecracker_sandbox_builds_command(monkeypatch, tmp_path: Path):
    kernel = tmp_path / "vmlinux"
    rootfs = tmp_path / "rootfs.ext4"
    kernel.write_bytes(b"kernel")
    rootfs.write_bytes(b"rootfs")

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/firectl" if name == "firectl" else "/usr/bin/firecracker")

    captured = {}

    def fake_run(cmd, cwd=None, capture_output=True, text=True, timeout=None):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    sandbox = FirecrackerSandbox(
        kernel_image=kernel,
        rootfs_image=rootfs,
        workspace=tmp_path,
        resources=FirecrackerResources(vcpu_count=2, memory_mib=512),
        network=None,
        egress_allowed=False,
    )
    sandbox.run(["/bin/true"])
    cmd_list = captured["cmd"]
    assert sandbox.firectl_bin in cmd_list[0]
    assert "--tap-device" not in cmd_list
