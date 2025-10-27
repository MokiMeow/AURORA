"""Load executor configuration from YAML profiles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .config import (
    CIPipelineStep,
    CIProfile,
    DockerConfig,
    ExecutorConfig,
    FirecrackerConfig,
    SandboxPolicies,
)


def load_executor_config(workspace: Path, config_path: Path) -> ExecutorConfig:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    profiles_data = data.get("profiles", data)
    profiles = {}
    raw_profiles = {}
    for name, profile_data in profiles_data.items():
        raw_profiles[name] = profile_data
    for name, profile_data in profiles_data.items():
        base_steps = profile_data.get("steps", [])
        extends = profile_data.get("extends")
        if extends and extends in raw_profiles:
            inherited = raw_profiles[extends].get("steps", [])
            base_steps = inherited + base_steps
        profile = CIProfile(
            name=name,
            steps=tuple(
                CIPipelineStep(
                    name=step["name"],
                    command=step["command"],
                    fail_fast=step.get("fail_fast"),
                )
                for step in base_steps
            ),
            timeout_minutes=profile_data.get("timeout_minutes", 30),
            fail_fast=profile_data.get("fail_fast", False),
        )
        profiles[name] = profile
    sandbox_cfg = data.get("runtime", {})
    default_runtime = sandbox_cfg.get("default", "docker")
    docker_cfg = sandbox_cfg.get("options", {}).get("docker", {})
    firecracker_cfg = None
    fc_opt = sandbox_cfg.get("options", {}).get("firecracker")
    if fc_opt and fc_opt.get("enabled", False):
        resources = fc_opt.get("resources", {})
        network_cfg = fc_opt.get("network")
        snapshot_dir = fc_opt.get("snapshot_dir")
        firecracker_cfg = FirecrackerConfig(
            kernel_image=Path(fc_opt["kernel_image"]),
            rootfs_image=Path(fc_opt["rootfs"]),
            resources=resources or None,
            network=network_cfg or None,
            snapshot_dir=Path(snapshot_dir) if snapshot_dir else None,
            firecracker_bin=fc_opt.get("firecracker_bin", "firecracker"),
            firectl_bin=fc_opt.get("firectl_bin", "firectl"),
        )
    policies_cfg = sandbox_cfg.get("policies", {})
    sandbox_policies = SandboxPolicies(
        egress_allowed=policies_cfg.get("egress", False),
        storage_mounts=policies_cfg.get("storage_mounts", []),
        allowlist=policies_cfg.get("allowlist"),
    )
    docker_mount_entries: list[dict[str, object]] = []
    for mount in docker_cfg.get("mounts", []):
        source = Path(mount["source"])
        if not source.is_absolute():
            source = workspace / source
        docker_mount_entries.append(
            {"source": str(source), "target": mount["target"], "readonly": mount.get("readonly", True)}
        )
    docker_config = DockerConfig(
        image=docker_cfg.get("image", "aurora-se/runtime:latest"),
        mounts=docker_mount_entries,
        env=docker_cfg.get("env"),
        network=docker_cfg.get("network"),
        seccomp_profile=Path(docker_cfg["seccomp_profile"]) if docker_cfg.get("seccomp_profile") else None,
        apparmor_profile=docker_cfg.get("apparmor_profile"),
        cpu_limit=_maybe_float(docker_cfg.get("cpu_limit")),
        memory_limit=docker_cfg.get("memory_limit"),
        read_only_root=docker_cfg.get("read_only_root", True),
        additional_args=tuple(docker_cfg.get("args", [])),
    )
    return ExecutorConfig(
        workspace=workspace,
        profiles=profiles,
        sandbox=default_runtime,
        artifacts_dir=workspace / "artifacts",
        policy_path=Path(data.get("policy_path", "policies/security.yaml")),
        docker=docker_config,
        firecracker_config=firecracker_cfg,
        sandbox_policies=sandbox_policies,
    )


def _maybe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

