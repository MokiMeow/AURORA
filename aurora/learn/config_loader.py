"""Load training configuration from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import (
    AccelerateConfig,
    DatasetConfig,
    HardwareConfig,
    LoRAConfig,
    MetadataConfig,
    SchedulerConfig,
    TrainingConfig,
)


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
        prefer_gpu=hardware_section.get("prefer_gpu", True),
    )
    lora_section = training.get("lora", {})
    lora = LoRAConfig(
        rank=lora_section.get("r", 8),
        alpha=lora_section.get("alpha", 16),
        dropout=lora_section.get("dropout", 0.1),
        target_modules=tuple(lora_section.get("target_modules", [])),
        target_modules_pattern=tuple(lora_section.get("target_modules_pattern", [])),
        scaling=lora_section.get("scaling", 1.0),
    )
    prompts = tuple(training.get("regularization_prompts", []))

    dataset_section = training.get("dataset", {})
    dataset_path = root / dataset_section.get("path", training.get("dataset_path", "experience/log.jsonl"))
    dataset = DatasetConfig(
        path=dataset_path,
        sample_size=dataset_section.get("sample_size", training.get("sample_size", 128)),
        min_reward=dataset_section.get("min_reward", training.get("min_reward", 0.0)),
        stratify_by=tuple(dataset_section.get("stratify_by", ("reward",))),
        reject_keywords=tuple(dataset_section.get("reject_keywords", ())),
        augmentations=tuple(dataset_section.get("augmentations", ())),
        balance_labels=dataset_section.get("balance_labels", True),
        holdout_fraction=float(dataset_section.get("holdout_fraction", 0.1)),
        max_group_size=int(dataset_section.get("max_group_size", 256)),
    )

    accelerate_section = training.get("accelerate", {})
    accelerate = AccelerateConfig(
        mixed_precision=accelerate_section.get("mixed_precision", "bf16"),
        gradient_accumulation_steps=accelerate_section.get("gradient_accumulation_steps", 1),
        gradient_checkpointing=accelerate_section.get("gradient_checkpointing", False),
        deepspeed_config=(root / accelerate_section["deepspeed_config"]) if accelerate_section.get("deepspeed_config") else None,
        device_map=accelerate_section.get("device_map", "auto"),
        use_int8=accelerate_section.get("use_int8", False),
        compile_model=accelerate_section.get("compile_model", False),
    )

    scheduler_section = training.get("scheduler", {})
    scheduler = SchedulerConfig(
        interactive=scheduler_section.get("interactive", False),
        nightly_cron=scheduler_section.get("nightly_cron"),
        batch_profiles=tuple(scheduler_section.get("batch_profiles", ())),
        post_run_hooks=tuple(scheduler_section.get("post_run_hooks", ())),
        telemetry_tags=tuple(scheduler_section.get("telemetry_tags", ())),
    )

    metadata_section = training.get("metadata", {})
    metadata = MetadataConfig(
        schema_path=root / metadata_section.get("schema_path", "configs/schemas/adapter_metadata.schema.json"),
        changelog_path=root / metadata_section.get("changelog_path", "artifacts/adapters/changelog.json"),
        provenance_path=root / metadata_section.get("provenance_path", "artifacts/adapters/provenance.jsonl"),
        signing_key_path=(root / metadata_section["signing_key_path"]) if metadata_section.get("signing_key_path") else None,
    )

    federation_section = data.get("federation", {})
    federation_enabled = federation_section.get("enabled", False)
    federation_path = federation_section.get("config_path")
    return TrainingConfig(
        adapters_path=adapters_path,
        base_model=training.get("base_model", "sshleifer/tiny-gpt2"),
        domain=domain,
        adapter_version=version,
        output_adapter=output_adapter,
        hardware=hardware,
        lora=lora,
        regularization_prompts=prompts,
        bias_report_path=root / training.get("bias_report", "artifacts/bias_reports/latest.json"),
        dataset=dataset,
        accelerate=accelerate,
        scheduler=scheduler,
        metadata=metadata,
        epochs=training.get("epochs", 1),
        learning_rate=training.get("learning_rate", 1e-4),
        bias_threshold=training.get("max_bias_score", 0.1),
        simulate=training.get("simulate", False),
        federation_config=(root / federation_path) if federation_enabled and federation_path else None,
        evaluation_suites=tuple(training.get("evaluation_suites", ())),
    )

