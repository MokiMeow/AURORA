"""Tests for secret scanning in executor."""

from pathlib import Path

from aurora.executor.service import ExecutorService
from aurora.executor.config import ExecutorConfig, CIProfile
from aurora.executor.ci import CIOrchestrator
from aurora.executor.policy import PolicyEvaluator
from aurora.security.secrets import SecretScanner, SecretScannerConfig


class DummyCI(CIOrchestrator):
    def __init__(self):
        self.ran = False

    def run_profile(self, profile, workdir: Path):
        self.ran = True
        return []


def test_executor_secret_scanner(tmp_path: Path):
    workspace = tmp_path
    config = ExecutorConfig(
        workspace=workspace,
        profiles={
            "fast": CIProfile(
                name="fast",
                steps=tuple(),
                timeout_minutes=10,
                fail_fast=False,
            )
        },
        sandbox="local",
        artifacts_dir=workspace,
    )
    ci = DummyCI()
    scanner = SecretScanner(SecretScannerConfig(patterns=(r"secret" ,)))
    policy = PolicyEvaluator(policy_path=None)
    executor = ExecutorService(config=config, ci_orchestrator=ci, secret_scanner=scanner, policy_evaluator=policy)

    edit_path = workspace / "edit.json"
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
    assert ci.ran is True

