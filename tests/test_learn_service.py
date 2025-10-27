"""Tests for learning service pipeline."""

import json
from pathlib import Path

from aurora.learn.config import HardwareConfig, TrainingConfig, LoRAConfig
from aurora.learn.service import LearningService


def test_learning_service_registers_adapter(tmp_path: Path):
    report_path = tmp_path / "bias.json"
    log_path = tmp_path / "data"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        json.dumps({"context": {"task": "fix"}, "edit": {"summary": "patch"}, "reward": 0.5}) + "\n",
        encoding="utf-8",
    )
    config = TrainingConfig(
        adapters_path=tmp_path / "adapters",
        data_path=log_path,
        base_model="base-model",
        domain="core",
        output_adapter=tmp_path / "output" / "adapter",
        hardware=HardwareConfig(gpu_memory_gb=24, fallback_mode="cpu", precision="8bit"),
        lora=LoRAConfig(rank=8, alpha=16, dropout=0.1, target_modules=("q_proj",)),
        sample_size=64,
        min_reward=0.1,
        regularization_prompts=("prompt",),
        bias_report_path=report_path,
        simulate=True,
    )
    service = LearningService(config)
    service.run(nightly=False)
    adapters = list((tmp_path / "adapters").glob("**/metadata.json"))
    assert adapters
    assert report_path.exists()

