"""Configuration models for learning pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass(slots=True)
class HardwareConfig:
    gpu_memory_gb: int
    fallback_mode: str
    precision: str


@dataclass(slots=True)
class LoRAConfig:
    rank: int
    alpha: int
    dropout: float
    target_modules: Tuple[str, ...]


@dataclass(slots=True)
class TrainingConfig:
    adapters_path: Path
    data_path: Path
    base_model: str
    domain: str
    output_adapter: Path
    hardware: HardwareConfig
    lora: LoRAConfig
    sample_size: int
    min_reward: float
    regularization_prompts: Tuple[str, ...]
    bias_report_path: Path
    epochs: int = 2
    learning_rate: float = 1e-4
    bias_threshold: float = 0.05
    simulate: bool = False
    federation_config: Optional[Path] = None

