"""Evaluation service for running SWE-Bench test suites."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class EvaluationConfig:
    suite: str
    output_dir: Path


class EvaluationService:
    def __init__(self, config: EvaluationConfig) -> None:
        self._config = config

    def run(self) -> Path:
        self._config.output_dir.mkdir(parents=True, exist_ok=True)
        result_path = self._config.output_dir / f"{self._config.suite}_results.json"
        result_path.write_text("{}", encoding="utf-8")
        return result_path

