"""Tests for secret scanning in executor."""

import subprocess
from pathlib import Path

from aurora.executor.config import CIPipelineStep, CIProfile, ExecutorConfig
from aurora.executor.ci import CIOrchestrator
from aurora.executor.policy import PolicyEvaluator
from aurora.executor.sandbox import SandboxRunner, SandboxResult
from aurora.executor.service import ExecutorService
from aurora.security.secrets import SecretScanner, SecretScannerConfig


class StubSandbox(SandboxRunner):
    def run(self, command, workdir=None, timeout=None, env=None):  # type: ignore[override]
        return SandboxResult(returncode=0, stdout="ok", stderr="")


def test_executor_secret_scanner(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    config = ExecutorConfig(
        workspace=tmp_path,
        profiles={
            "fast": CIProfile(
                name="fast",
                steps=(CIPipelineStep(name="noop", command=["echo", "ok"]),),
                timeout_minutes=10,
                fail_fast=False,
            )
        },
        sandbox="local",
        artifacts_dir=tmp_path / "artifacts",
    )
    orchestrator = CIOrchestrator(sandbox=StubSandbox(), artifacts_dir=config.artifacts_dir)
    scanner = SecretScanner(SecretScannerConfig(patterns=(r"secret",)))
    policy = PolicyEvaluator(policy_path=None)
    executor = ExecutorService(
        config=config,
        ci_orchestrator=orchestrator,
        secret_scanner=scanner,
        policy_evaluator=policy,
        approval_callback=lambda _: True,
    )

    edit_path = tmp_path / "edit.json"
    edit_path.write_text(
        """
{
  "intent": "bugfix",
  "summary": "",
  "plan": [],
  "graph_targets": [],
  "patches": [],
  "tests": [],
  "tools": {},
  "train": {"enable": false},
  "acceptance": {"min_R": 0, "security_zero_criticals": true}
}
""",
        encoding="utf-8",
    )

    executor.apply(edit_path=edit_path, profile="fast")

