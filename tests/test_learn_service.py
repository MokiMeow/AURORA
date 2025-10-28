"""Tests for learning service pipeline."""

import json
from pathlib import Path

from aurora.learn.config_loader import load_training_config
from aurora.learn.service import LearningService


def test_learning_service_registers_adapter(tmp_path: Path):
    experience_log = tmp_path / "experience" / "log.jsonl"
    experience_log.parent.mkdir(parents=True, exist_ok=True)
    experience_log.write_text(
        json.dumps({"context": {"task": "fix"}, "edit": {"summary": "patch"}, "reward": 0.8}) + "\n",
        encoding="utf-8",
    )

    schema_path = Path.cwd() / "configs" / "schemas" / "adapter_metadata.schema.json"
    changelog_path = tmp_path / "artifacts" / "changelog.json"
    provenance_path = tmp_path / "artifacts" / "provenance.jsonl"
    config_file = tmp_path / "learn.yaml"
    config_file.write_text(
        f"""
training:
  adapters_path: adapters
  base_model: base-model
  domain: core
  adapter_version: 0.3.0
  output_root: adapters
  bias_report: artifacts/bias.json
  epochs: 2
  learning_rate: 0.0002
  max_bias_score: 0.3
  evaluation_suites: []
  dataset:
    path: "{experience_log.as_posix()}"
    sample_size: 4
    min_reward: 0.1
    stratify_by: ['reward']
    reject_keywords: []
    augmentations: []
    balance_labels: false
    holdout_fraction: 0.0
    max_group_size: 8
  lora:
    r: 4
    alpha: 8
    dropout: 0.05
    scaling: 1.0
    target_modules: [q_proj]
    target_modules_pattern: []
  accelerate:
    mixed_precision: bf16
    gradient_accumulation_steps: 1
    gradient_checkpointing: false
    device_map: auto
    use_int8: false
    compile_model: false
  scheduler:
    interactive: false
    nightly_cron:
    batch_profiles: []
    post_run_hooks: []
    telemetry_tags: []
  metadata:
    schema_path: "{schema_path.as_posix()}"
    changelog_path: "{changelog_path.as_posix()}"
    provenance_path: "{provenance_path.as_posix()}"
  regularization_prompts: []
  simulate: true
  hardware:
    gpu_memory_gb: 12
    fallback_mode: cpu
    precision: 8bit
    prefer_gpu: false
        """,
        encoding="utf-8",
    )

    config = load_training_config(tmp_path, config_file)
    service = LearningService(config)
    service.run(nightly=False)

    adapters = list((tmp_path / "adapters").glob("**/metadata.json"))
    assert adapters
    bias_report = config.bias_report_path
    assert bias_report.exists()
