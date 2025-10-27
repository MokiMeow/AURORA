"""CI profile runner for executor."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .config import CIProfile
from .sandbox import SandboxRunner

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CIResult:
    step: str
    success: bool
    output_path: Path


class CIOrchestrator:
    def __init__(self, sandbox: SandboxRunner, artifacts_dir: Path) -> None:
        self._sandbox = sandbox
        self._artifacts_dir = artifacts_dir
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run_profile(self, profile: CIProfile, workdir: Path) -> list[CIResult]:
        results: list[CIResult] = []
        for step in profile.steps:
            LOGGER.info("Running CI step %s", step.name)
            log_path = self._artifacts_dir / f"ci_{step.name}.log"
            try:
                self._sandbox.run(step.command, workdir=workdir)
                log_path.write_text("success", encoding="utf-8")
                results.append(CIResult(step=step.name, success=True, output_path=log_path))
            except Exception as exc:  # pragma: no cover
                log_path.write_text(str(exc), encoding="utf-8")
                results.append(CIResult(step=step.name, success=False, output_path=log_path))
                if step.fail_fast is True or profile.fail_fast:
                    break
        return results

