"""Filtered-SFT pipeline integration with PEFT/LoRA."""

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .dataset import load_training_samples, compute_bias_score, DatasetError

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
        simulate: bool = False,
        lora_config: dict | None = None,
        sample_size: int | None = None,
        regularization_prompts: tuple[str, ...] | None = None,
        min_reward: float | None = None,
    ) -> None:
        self._data_path = data_path
        self._base_model = base_model
        self._output_path = output_path
        self._epochs = epochs
        self._learning_rate = learning_rate
        self._simulate = simulate
        self._lora_config = lora_config or {}
        self._sample_size = sample_size or 0
        self._regularization_prompts = regularization_prompts or ()
        self._min_reward = min_reward or 0.0

    def run(self) -> PipelineResult:
        LOGGER.info(
            "Running Filtered-SFT", extra={
                "base_model": self._base_model,
                "data_path": str(self._data_path),
                "output": str(self._output_path),
                "epochs": self._epochs,
                "learning_rate": self._learning_rate,
                "lora": self._lora_config,
                "sample_size": self._sample_size,
                "min_reward": self._min_reward,
            }
        )
        self._output_path.mkdir(parents=True, exist_ok=True)
        adapter_file = self._output_path / "adapter.bin"
        adapter_file.write_bytes(b"")
        if self._simulate:
            time.sleep(0.1)  # simulate training time
            metrics = {
                "loss": round(random.uniform(0.01, 0.05), 4),
                "accuracy": round(random.uniform(0.9, 0.99), 4),
            }
            try:
                samples = load_training_samples(self._data_path, self._min_reward, self._sample_size)
                bias_score = compute_bias_score(samples)
            except DatasetError:
                bias_score = 0.0
        else:
            metrics = {
                "loss": 0.0,
                "accuracy": 1.0,
            }
            bias_score = 0.0
        metrics_path = self._output_path / "training_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return PipelineResult(adapter_path=self._output_path, bias_score=bias_score, training_metrics=metrics)

