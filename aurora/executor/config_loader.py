"""Load executor configuration from YAML profiles."""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import CIPipelineStep, CIProfile, ExecutorConfig, FirecrackerConfig, SandboxPolicies


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
        firecracker_cfg = FirecrackerConfig(
            kernel_image=Path(fc_opt["kernel_image"]),
            rootfs_image=Path(fc_opt["rootfs"]),
        )
    policies_cfg = sandbox_cfg.get("policies", {})
    sandbox_policies = SandboxPolicies(
        egress_allowed=policies_cfg.get("egress", False),
        storage_mounts=policies_cfg.get("storage_mounts", []),
    )
    return ExecutorConfig(
        workspace=workspace,
        profiles=profiles,
        sandbox=default_runtime,
        artifacts_dir=workspace / "artifacts",
        policy_path=Path(data.get("policy_path", "policies/security.yaml")),
        docker_image=docker_cfg.get("image"),
        docker_env=docker_cfg.get("env"),
        docker_mounts=docker_cfg.get("mounts"),
        firecracker_config=firecracker_cfg,
        sandbox_policies=sandbox_policies,
    )

