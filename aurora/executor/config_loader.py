"""Load executor configuration from YAML profiles."""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import CIPipelineStep, CIProfile, ExecutorConfig, FirecrackerConfig


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
    docker_cfg = data.get("docker", {})
    firecracker_cfg = None
    if "firecracker" in data:
        fc = data["firecracker"]
        firecracker_cfg = FirecrackerConfig(
            kernel_image=Path(fc["kernel_image"]),
            rootfs_image=Path(fc["rootfs_image"]),
        )
    return ExecutorConfig(
        workspace=workspace,
        profiles=profiles,
        sandbox=data.get("sandbox", "docker"),
        artifacts_dir=workspace / "artifacts",
        policy_path=Path(data.get("policy_path", "policies/security.yaml")),
        docker_image=docker_cfg.get("image"),
        docker_env=docker_cfg.get("env"),
        docker_mounts=docker_cfg.get("mounts"),
        firecracker_config=firecracker_cfg,
    )

