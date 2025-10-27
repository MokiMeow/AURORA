"""Tests for training config loader."""

from pathlib import Path

from aurora.learn.config_loader import load_training_config


def test_load_training_config(tmp_path: Path):
    config_file = tmp_path / "learn.yaml"
    config_file.write_text(
        """
training:
  adapters_path: adapters
  dataset_path: experience/log.jsonl
  base_model: test-model
  domain: core
  output_root: adapters
  adapter_version: 0.2.0
  sample_size: 32
  min_reward: 0.2
  epochs: 2
  learning_rate: 0.0002
  max_bias_score: 0.3
  simulate: true
  lora:
    r: 4
    alpha: 8
    dropout: 0.05
    target_modules:
      - q_proj
      - v_proj
  regularization_prompts:
    - prompt-one
    - prompt-two
  hardware:
    gpu_memory_gb: 12
    fallback_mode: cpu
    precision: 8bit
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
    assert config.lora.rank == 4
    assert config.sample_size == 32
    assert config.min_reward == 0.2
    assert config.simulate is True


