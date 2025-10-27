"""Evaluation service for running SWE-Bench suites and logging results."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..planner.pdca import PDCAEntry
from .config import EvaluationConfig, SuiteConfig

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class EvaluationResult:
    suite: str
    exit_code: int
    output_path: Path


class EvaluationService:
    def __init__(self, config: EvaluationConfig) -> None:
        self._config = config

    def run(self, suite_name: str) -> EvaluationResult:
        if suite_name not in self._config.suites:
            raise ValueError(f"Unknown evaluation suite {suite_name}")
        suite = self._config.suites[suite_name]
        suite.artifacts_dir.mkdir(parents=True, exist_ok=True)
        PDCAEntry(phase="Check", event="evaluation_start", payload={"suite": suite_name}).write()
        result_path = suite.artifacts_dir / f"{suite_name}_results.json"
        process = subprocess.run(
            suite.command,
            cwd=suite.dataset_path,
            capture_output=True,
            text=True,
        )
        result = {
            "suite": suite_name,
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
        }
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        PDCAEntry(
            phase="Check",
            event="evaluation_complete",
            payload={"suite": suite_name, "exit_code": process.returncode},
        ).write()
        return EvaluationResult(suite=suite_name, exit_code=process.returncode, output_path=result_path)

