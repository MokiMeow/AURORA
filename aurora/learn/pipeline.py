"""Filtered-SFT pipeline integration with PEFT/LoRA."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineResult:
    adapter_path: Path
    bias_score: float
    training_metrics: dict


class SFTPipeline:
    def __init__(
        self,
        data_path: Path,
        base_model: str,
        output_path: Path,
        epochs: int,
        learning_rate: float,
    ) -> None:
        self._data_path = data_path
        self._base_model = base_model
        self._output_path = output_path
        self._epochs = epochs
        self._learning_rate = learning_rate

    def run(self) -> PipelineResult:
        # Placeholder: integrate Hugging Face + PEFT/LoRA here.
        LOGGER.info(
            "Running Filtered-SFT", extra={
                "base_model": self._base_model,
                "data_path": str(self._data_path),
                "output": str(self._output_path),
                "epochs": self._epochs,
                "learning_rate": self._learning_rate,
            }
        )
        self._output_path.mkdir(parents=True, exist_ok=True)
        (self._output_path / "adapter.bin").write_bytes(b"")
        metrics = {
            "loss": 0.01,
            "accuracy": 0.99,
        }
        bias_score = 0.02
        metrics_path = self._output_path / "training_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return PipelineResult(adapter_path=self._output_path, bias_score=bias_score, training_metrics=metrics)

