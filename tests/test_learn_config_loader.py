"""Tests for training config loader."""

from pathlib import Path

from aurora.learn.config_loader import load_training_config


def test_load_training_config(tmp_path: Path):
    config_file = tmp_path / "learn.yaml"
    config_file.write_text(
        """
training:
  adapters_path: adapters
  base_model: test-model
  domain: core
  output_root: adapters
  adapter_version: 0.2.0
  simulate: true
  epochs: 2
  learning_rate: 0.0002
  max_bias_score: 0.3
  evaluation_suites:
    - lite-smoke
  dataset:
    path: experience/log.jsonl
    sample_size: 32
    min_reward: 0.2
    stratify_by:
      - reward
      - length
    reject_keywords:
      - secret
    augmentations:
      - prompt_noise
    balance_labels: true
    holdout_fraction: 0.2
    max_group_size: 64
  lora:
    r: 4
    alpha: 8
    dropout: 0.05
    scaling: 1.2
    target_modules:
      - q_proj
      - v_proj
    target_modules_pattern:
      - 'layers\\d+\\.self_attn'
  accelerate:
    mixed_precision: bf16
    gradient_accumulation_steps: 4
    gradient_checkpointing: true
    device_map: auto
    use_int8: false
    compile_model: true
  scheduler:
    interactive: true
    nightly_cron: "0 3 * * *"
    batch_profiles:
      - nightly
    post_run_hooks:
      - scripts/hooks/notify_slack.py
    telemetry_tags:
      - training
  metadata:
    schema_path: configs/schemas/adapter_metadata.schema.json
    changelog_path: artifacts/adapters/changelog.json
    provenance_path: artifacts/adapters/provenance.jsonl
  regularization_prompts:
    - prompt-one
    - prompt-two
  hardware:
    gpu_memory_gb: 12
    fallback_mode: cpu
    precision: 8bit
    prefer_gpu: false
federation:
  enabled: true
  config_path: configs/federation.yaml
        """,
        encoding="utf-8",
    )
    config = load_training_config(tmp_path, config_file)
    assert config.adapters_path == tmp_path / "adapters"
    assert config.domain == "core"
    assert config.output_adapter == tmp_path / "adapters" / "core" / "0.2.0"
    assert config.adapter_version == "0.2.0"
    assert config.lora.rank == 4
    assert config.lora.scaling == 1.2
    assert config.dataset.sample_size == 32
    assert config.dataset.balance_labels is True
    assert config.accelerate.gradient_accumulation_steps == 4
    assert config.scheduler.nightly_cron == "0 3 * * *"
    assert config.metadata.schema_path == tmp_path / "configs/schemas/adapter_metadata.schema.json"
    assert config.simulate is True


