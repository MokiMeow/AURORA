"""Load executor configuration from YAML profiles."""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import CIPipelineStep, CIProfile, ExecutorConfig


def load_executor_config(workspace: Path, config_path: Path) -> ExecutorConfig:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    profiles = {}
    for name, profile_data in data.items():
        profile = CIProfile(
            name=name,
            steps=tuple(
                CIPipelineStep(
                    name=step["name"],
                    command=step["command"].split(),
                    fail_fast=step.get("fail_fast"),
                )
                for step in profile_data["steps"]
            ),
            timeout_minutes=profile_data.get("timeout_minutes", 30),
            fail_fast=profile_data.get("fail_fast", False),
        )
        profiles[name] = profile
    return ExecutorConfig(
        workspace=workspace,
        profiles=profiles,
        sandbox="docker",
        artifacts_dir=workspace / "artifacts",
        policy_path=Path("policies/security.yaml"),
    )

