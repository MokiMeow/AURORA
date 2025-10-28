"""Executor service responsible for applying self-edits and running CI."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Iterable

from ..planner.schema import SelfEdit
from ..security.secrets import SecretScanner
from .patch import apply as apply_patch, apply_three_way, dry_run as dry_run_patch, diff_summary, detect_test_deletions
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
        approval_callback: Callable[[str], bool] | None = None,
        approval_timeout: int = 300,
    ) -> None:
        self._config = config
        self._ci_orchestrator = ci_orchestrator
        self._secret_scanner = secret_scanner
        self._policy_evaluator = policy_evaluator
        self._fatal_failures = 0
        self._circuit_breaker_limit = circuit_breaker_limit
        self._error_log = error_log
        self._approval_callback = approval_callback
        self._approval_timeout = approval_timeout

    def apply(self, edit_path: Path, profile: str) -> None:
        if self._fatal_failures >= self._circuit_breaker_limit:
            raise RuntimeError("Circuit breaker tripped; executor halted")
        if not edit_path.exists():
            raise FileNotFoundError(f"Edit file {edit_path} does not exist")
        self._check_workspace_clean(allowed=(edit_path,))
        self_edit = SelfEdit.model_validate_json(edit_path.read_text(encoding="utf-8"))
        self._config.artifacts_dir.mkdir(parents=True, exist_ok=True)
        correlation_id = str(uuid.uuid4())
        PDCAEntry(
            phase="Do",
            event="start",
            payload={"intent": self_edit.intent, "profile": profile, "correlation_id": correlation_id},
        )
        try:
            self._apply_patches(self_edit.patches)
            self._scan_for_secrets()
            self._write_diff_artifacts(correlation_id)
            self._await_manual_approval(correlation_id)
            results = self._run_ci(profile)
        except PatchApplicationError as exc:
            self._fatal_failures += 1
            self._log_error("fatal", str(exc))
            PDCAEntry(phase="Do", event="failure", payload={"type": "fatal", "error": str(exc)})
            raise
        except Exception as exc:  # pragma: no cover - safety net
            self._fatal_failures += 1
            PDCAEntry(
                phase="Act",
                event="failure",
                payload={"error": str(exc), "fatal_failures": self._fatal_failures},
            )
            raise
        summary = diff_summary(self._config.workspace)
        ci_payload = [
            {
                "step": result.step,
                "success": result.success,
                "log": str(result.output_path),
                "started_at": result.started_at,
                "duration_seconds": result.duration_seconds,
                "attempts": result.attempts,
                "message": result.message,
                "correlation_id": result.correlation_id,
            }
            for result in results
        ]
        PDCAEntry(
            phase="Check",
            event="ci_results",
            payload={"profile": profile, "results": ci_payload, "diff": summary, "correlation_id": correlation_id},
        )
        policy_metadata = self._collect_policy_metadata()
        policy_result = self._policy_evaluator.evaluate(ci_payload, policy_metadata)
        if not policy_result.accepted:
            PDCAEntry(phase="Act", event="policy_reject", payload={"reasons": policy_result.reasons})
            self._fatal_failures += 1
            self._log_error("fatal", "Policy failure: " + "; ".join(policy_result.reasons))
            raise RuntimeError("Policy evaluation failed: " + "; ".join(policy_result.reasons))
        summary_path = self._config.artifacts_dir / "executor_summary.json"
        summary_path.write_text(json.dumps({"ci_results": ci_payload, "policy": policy_result.reasons}, indent=2))
        PDCAEntry(phase="Act", event="completed", payload={"profile": profile, "correlation_id": correlation_id})

    def _apply_patches(self, patches: Iterable[Any]) -> None:
        for patch in patches:
            if isinstance(patch, dict):
                diff = patch["diff"]
            else:
                diff = getattr(patch, "diff")
            dry_run_patch(diff, self._config.workspace)
            deletions = detect_test_deletions(diff)
            if deletions:
                raise PatchApplicationError(f"Patch deletes tests: {deletions}")
            try:
                apply_patch(diff, self._config.workspace)
            except PatchApplicationError as exc:
                LOGGER.warning("Patch failed, attempting three-way merge: %s", exc)
                try:
                    apply_three_way(diff, self._config.workspace)
                except PatchApplicationError as merge_exc:
                    self._log_error("patch", str(merge_exc))
                    raise PatchApplicationError(
                        f"Patch failed to apply even with three-way merge.\n{merge_exc}"
                    ) from merge_exc

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

    def _collect_policy_metadata(self) -> dict[str, Any]:
        artifacts = self._config.artifacts_dir
        metadata: dict[str, Any] = {}
        for name, filename in (
            ("sbom", "sbom.json"),
            ("cve_report", "cve_report.json"),
            ("license_report", "license_report.json"),
            ("diff_explainer", "diff_explainer.md"),
        ):
            path = artifacts / filename
            if path.exists():
                try:
                    if filename.endswith(".json"):
                        metadata[name] = json.loads(path.read_text(encoding="utf-8"))
                    else:
                        metadata[name] = path.read_text(encoding="utf-8")
                except json.JSONDecodeError:
                    metadata[name] = {"error": "invalid_json"}
        metadata["artifacts_dir"] = str(artifacts)
        return metadata

    def _check_workspace_clean(self, allowed: Iterable[Path] | None = None) -> None:
        if not (self._config.workspace / ".git").exists():
            return
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self._config.workspace,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError("Unable to inspect workspace status before applying patches")
        allowed_rel = set()
        if allowed:
            for path in allowed:
                try:
                    relative = path.relative_to(self._config.workspace)
                except ValueError:
                    continue
                allowed_rel.add(str(relative).replace("\\", "/"))
        dirty_lines = [
            line
            for line in result.stdout.splitlines()
            if not line.strip().startswith("?? artifacts")
        ]
        if allowed_rel:
            filtered = []
            for line in dirty_lines:
                token = line.strip().split(" ", 1)[-1]
                if token in allowed_rel:
                    continue
                filtered.append(line)
            dirty_lines = filtered
        if dirty_lines:
            raise RuntimeError(
                "Workspace has uncommitted changes. Please clean before running executor: "
                + ", ".join(dirty_lines[:5])
            )

    def _write_diff_artifacts(self, correlation_id: str) -> None:
        artifacts = self._config.artifacts_dir
        artifacts.mkdir(parents=True, exist_ok=True)
        if not (self._config.workspace / ".git").exists():
            return
        stat_proc = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=self._config.workspace,
            capture_output=True,
            text=True,
        )
        if stat_proc.returncode != 0:
            LOGGER.warning("git diff --stat failed: %s", stat_proc.stderr)
            return
        numstat_proc = subprocess.run(
            ["git", "diff", "--numstat"],
            cwd=self._config.workspace,
            capture_output=True,
            text=True,
        )
        full_proc = subprocess.run(
            ["git", "diff"],
            cwd=self._config.workspace,
            capture_output=True,
            text=True,
        )
        stat = stat_proc.stdout
        numstat = numstat_proc.stdout
        full_diff = full_proc.stdout
        md_path = artifacts / "diff_explainer.md"
        md_path.write_text(
            (
                f"# Diff Summary ({correlation_id})\n\n"
                "## Changes by file\n\n"
                f"```\n{stat.strip()}\n```\n\n"
                "## Detailed hunks\n\n"
                f"```\n{full_diff.strip()}\n```\n"
            ),
            encoding="utf-8",
        )
        json_path = artifacts / "diff_explainer.json"
        json_path.write_text(
            json.dumps(
                {
                    "correlation_id": correlation_id,
                    "stat": stat.strip(),
                    "numstat": numstat.strip(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _await_manual_approval(self, correlation_id: str) -> None:
        if os.getenv("AURORA_REQUIRE_APPROVAL") != "1":
            return
        PDCAEntry(
            phase="Do",
            event="awaiting_approval",
            payload={"correlation_id": correlation_id},
        )
        if self._approval_callback:
            approved = self._approval_callback(correlation_id)
            if not approved:
                raise RuntimeError("Manual approval denied for executor run")
            return
        approval_file = Path(os.getenv("AURORA_APPROVAL_FILE", self._config.artifacts_dir / "approval_token.txt"))
        deadline = time.time() + self._approval_timeout
        while time.time() < deadline:
            if approval_file.exists():
                decision = approval_file.read_text(encoding="utf-8").strip().lower()
                if decision == "approve":
                    return
                if decision == "reject":
                    raise RuntimeError("Manual approval rejected via token file")
            time.sleep(1)
        raise RuntimeError("Manual approval timeout reached")

