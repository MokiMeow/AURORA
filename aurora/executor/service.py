"""Executor service responsible for applying self-edits and running CI."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ..planner.schema import SelfEdit
from ..security.secrets import SecretScanner
from .patch import apply as apply_patch, dry_run as dry_run_patch, rollback as rollback_patch, diff_summary, detect_test_deletions, PatchError
from ..planner.pdca import PDCAEntry
from .ci import CIOrchestrator
from .config import ExecutorConfig
from .policy import PolicyEvaluator

LOGGER = logging.getLogger(__name__)


class PatchApplicationError(RuntimeError):
    """Raised when patch application fails."""


class ExecutorService:
    def __init__(
        self,
        config: ExecutorConfig,
        ci_orchestrator: CIOrchestrator,
        secret_scanner: SecretScanner,
        policy_evaluator: PolicyEvaluator,
        circuit_breaker_limit: int = 3,
        error_log: Path | None = Path("telemetry/errors.jsonl"),
    ) -> None:
        self._config = config
        self._ci_orchestrator = ci_orchestrator
        self._secret_scanner = secret_scanner
        self._policy_evaluator = policy_evaluator
        self._fatal_failures = 0
        self._circuit_breaker_limit = circuit_breaker_limit
        self._error_log = error_log

    def apply(self, edit_path: Path, profile: str) -> None:
        if self._fatal_failures >= self._circuit_breaker_limit:
            raise RuntimeError("Circuit breaker tripped; executor halted")
        if not edit_path.exists():
            raise FileNotFoundError(f"Edit file {edit_path} does not exist")
        self_edit = SelfEdit.model_validate_json(edit_path.read_text(encoding="utf-8"))
        PDCAEntry(phase="Do", event="start", payload={"intent": self_edit.intent, "profile": profile}).write()
        try:
            self._apply_patches(self_edit.patches)
            self._scan_for_secrets()
            results = self._run_ci(profile)
        except PatchApplicationError as exc:
            self._fatal_failures += 1
            self._log_error("fatal", str(exc))
            PDCAEntry(phase="Do", event="failure", payload={"type": "fatal", "error": str(exc)}).write()
            raise
        except Exception as exc:
            self._log_error("retryable", str(exc))
            PDCAEntry(phase="Do", event="failure", payload={"type": "retryable", "error": str(exc)}).write()
            raise
        summary = diff_summary(self._config.workspace)
        ci_payload = [
            {"step": result.step, "success": result.success, "log": str(result.output_path)}
            for result in results
        ]
        PDCAEntry(
            phase="Check",
            event="ci_results",
            payload={"profile": profile, "results": ci_payload, "diff": summary},
        ).write()
        policy_result = self._policy_evaluator.evaluate(ci_payload)
        if not policy_result.accepted:
            PDCAEntry(phase="Act", event="policy_reject", payload={"reasons": policy_result.reasons}).write()
            self._fatal_failures += 1
            self._log_error("fatal", "Policy failure: " + "; ".join(policy_result.reasons))
            raise RuntimeError("Policy evaluation failed: " + "; ".join(policy_result.reasons))
        summary_path = self._config.artifacts_dir / "executor_summary.json"
        summary_path.write_text(json.dumps({"ci_results": ci_payload, "policy": policy_result.reasons}, indent=2))
        PDCAEntry(phase="Act", event="completed", payload={"profile": profile}).write()

    def _apply_patches(self, patches: Iterable[dict]) -> None:
        for patch in patches:
            diff = patch["diff"]
            dry_run_patch(diff, self._config.workspace)
            deletions = detect_test_deletions(diff)
            if deletions:
                raise PatchApplicationError(f"Patch deletes tests: {deletions}")
            apply_patch(diff, self._config.workspace)

    def _scan_for_secrets(self) -> None:
        for path in self._config.workspace.rglob("*"):
            if path.is_file():
                found, _ = self._secret_scanner.scan_file(path)
                if found:
                    raise RuntimeError(f"Secret detected in {path}")

    def _run_ci(self, profile_name: str):
        profile = self._config.profiles.get(profile_name)
        if not profile:
            raise ValueError(f"Unknown CI profile {profile_name}")
        return self._ci_orchestrator.run_profile(profile, workdir=self._config.workspace)

    def _log_error(self, category: str, message: str) -> None:
        if not self._error_log:
            return
        record = {"category": category, "message": message}
        self._error_log.parent.mkdir(parents=True, exist_ok=True)
        with self._error_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

