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
    prefer_gpu: bool


@dataclass(slots=True)
class LoRAConfig:
    rank: int
    alpha: int
    dropout: float
    target_modules: Tuple[str, ...]
    target_modules_pattern: Tuple[str, ...]
    scaling: float


@dataclass(slots=True)
class DatasetConfig:
    path: Path
    sample_size: int
    min_reward: float
    stratify_by: Tuple[str, ...]
    reject_keywords: Tuple[str, ...]
    augmentations: Tuple[str, ...]
    balance_labels: bool
    holdout_fraction: float
    max_group_size: int


@dataclass(slots=True)
class AccelerateConfig:
    mixed_precision: str
    gradient_accumulation_steps: int
    gradient_checkpointing: bool
    deepspeed_config: Optional[Path]
    device_map: str
    use_int8: bool
    compile_model: bool


@dataclass(slots=True)
class SchedulerConfig:
    interactive: bool
    nightly_cron: Optional[str]
    batch_profiles: Tuple[str, ...]
    post_run_hooks: Tuple[str, ...]
    telemetry_tags: Tuple[str, ...]


@dataclass(slots=True)
class MetadataConfig:
    schema_path: Path
    changelog_path: Path
    provenance_path: Path
    signing_key_path: Optional[Path]


@dataclass(slots=True)
class TrainingConfig:
    adapters_path: Path
    base_model: str
    domain: str
    adapter_version: str
    output_adapter: Path
    hardware: HardwareConfig
    lora: LoRAConfig
    regularization_prompts: Tuple[str, ...]
    bias_report_path: Path
    dataset: DatasetConfig
    accelerate: AccelerateConfig
    scheduler: SchedulerConfig
    metadata: MetadataConfig
    epochs: int = 2
    learning_rate: float = 1e-4
    bias_threshold: float = 0.05
    simulate: bool = False
    federation_config: Optional[Path] = None
    evaluation_suites: Tuple[str, ...] = ()

