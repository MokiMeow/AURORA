"""CI profile runner for executor."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Dict
from uuid import uuid4

from .config import CIProfile, CIPipelineStep
from .sandbox import SandboxRunner, SandboxError

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CIResult:
    step: str
    success: bool
    output_path: Path
    started_at: str
    duration_seconds: float
    attempts: int
    correlation_id: str
    message: str = ""


class CIOrchestrator:
    def __init__(self, sandbox: SandboxRunner, artifacts_dir: Path) -> None:
        self._sandbox = sandbox
        self._artifacts_dir = artifacts_dir
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run_profile(self, profile: CIProfile, workdir: Path) -> list[CIResult]:
        results: list[CIResult] = []
        correlation_id = str(uuid4())
        dependency_status: Dict[str, bool] = {}
        for step in profile.steps:
            LOGGER.info("Running CI step %s", step.name)
            log_path = self._artifacts_dir / f"ci_{step.name}.log"
            start = time()
            attempts = 0
            success = False
            message = ""

            if step.depends_on and not self._dependencies_satisfied(step, dependency_status):
                message = "Skipped due to failed dependencies"
                log_path.write_text(message, encoding="utf-8")
                results.append(
                    CIResult(
                        step=step.name,
                        success=False,
                        output_path=log_path,
                        started_at=self._format_time(start),
                        duration_seconds=0.0,
                        attempts=0,
                        correlation_id=correlation_id,
                        message=message,
                    )
                )
                dependency_status[step.name] = False
                if step.fail_fast or profile.fail_fast:
                    break
                continue

            timeout_seconds = None
            if step.timeout_minutes:
                timeout_seconds = step.timeout_minutes * 60
            elif profile.timeout_minutes:
                timeout_seconds = profile.timeout_minutes * 60

            while attempts <= step.retries:
                attempts += 1
                try:
                    sandbox_result = self._sandbox.run(
                        step.command,
                        workdir=workdir,
                        timeout=timeout_seconds,
                        env=step.env,
                    )
                    message = sandbox_result.stdout or "success"
                    log_path.write_text(
                        message + ("\n" + sandbox_result.stderr if sandbox_result.stderr else ""),
                        encoding="utf-8",
                    )
                    success = True
                    break
                except SandboxError as exc:
                    message = str(exc)
                    if attempts > step.retries:
                        log_path.write_text(message, encoding="utf-8")
                        success = False
                    else:
                        LOGGER.warning("Retrying CI step %s (%s)", step.name, exc)
                except Exception as exc:  # pragma: no cover - defensive
                    message = str(exc)
                    log_path.write_text(message, encoding="utf-8")
                    success = False
                    break

            duration = time() - start
            results.append(
                CIResult(
                    step=step.name,
                    success=success,
                    output_path=log_path,
                    started_at=self._format_time(start),
                    duration_seconds=duration,
                    attempts=attempts,
                    correlation_id=correlation_id,
                    message=message,
                )
            )
            dependency_status[step.name] = success
            if not success and (step.fail_fast or profile.fail_fast):
                break
        return results

    def _dependencies_satisfied(self, step: CIPipelineStep, status: Dict[str, bool]) -> bool:
        return all(status.get(name, False) for name in step.depends_on)

    @staticmethod
    def _format_time(timestamp: float) -> str:
        return time_to_iso(timestamp)


def time_to_iso(timestamp: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()

