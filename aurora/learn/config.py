"""Configuration models for learning pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class HardwareConfig:
    gpu_memory_gb: int
    fallback_mode: str
    precision: str


@dataclass(slots=True)
class TrainingConfig:
    adapters_path: Path
    data_path: Path
    base_model: str
    output_adapter: Path
    hardware: HardwareConfig
    epochs: int = 2
    learning_rate: float = 1e-4
    bias_threshold: float = 0.05

