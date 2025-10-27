"""Load training configuration from YAML."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config import TrainingConfig, HardwareConfig, LoRAConfig


def load_training_config(root: Path, path: Path) -> TrainingConfig:
    data = yaml.safe_load(path.read_text())
    training = data["training"]
    adapters_path = root / training.get("adapters_path", "adapters")
    output_root = root / training.get("output_root", "adapters")
    domain = training.get("domain", "core")
    version = training.get("adapter_version", "0.0.1")
    output_adapter = output_root / domain / version
    hardware_section = training.get("hardware", {})
    hardware = HardwareConfig(
        gpu_memory_gb=hardware_section.get("gpu_memory_gb", 24),
        fallback_mode=hardware_section.get("fallback_mode", "cpu"),
        precision=hardware_section.get("precision", "8bit"),
    )
    lora_section = training.get("lora", {})
    lora = LoRAConfig(
        rank=lora_section.get("r", 8),
        alpha=lora_section.get("alpha", 16),
        dropout=lora_section.get("dropout", 0.1),
        target_modules=tuple(lora_section.get("target_modules", [])),
    )
    prompts = tuple(training.get("regularization_prompts", []))
    federation_section = data.get("federation", {})
    federation_enabled = federation_section.get("enabled", False)
    federation_path = federation_section.get("config_path")
    return TrainingConfig(
        adapters_path=adapters_path,
        data_path=root / training.get("dataset_path", "experience/log.jsonl"),
        base_model=training.get("base_model", "sshleifer/tiny-gpt2"),
        domain=domain,
        output_adapter=output_adapter,
        hardware=hardware,
        lora=lora,
        sample_size=training.get("sample_size", 128),
        min_reward=training.get("min_reward", 0.0),
        regularization_prompts=prompts,
        bias_report_path=root / training.get("bias_report", "artifacts/bias_reports/latest.json"),
        epochs=training.get("epochs", 1),
        learning_rate=training.get("learning_rate", 1e-4),
        bias_threshold=training.get("max_bias_score", 0.1),
        simulate=training.get("simulate", False),
        federation_config=(root / federation_path) if federation_enabled and federation_path else None,
    )

