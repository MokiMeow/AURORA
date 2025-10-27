"""Tests for learning service pipeline."""

from pathlib import Path

from aurora.learn.config import HardwareConfig, TrainingConfig
from aurora.learn.service import LearningService


def test_learning_service_registers_adapter(tmp_path: Path):
    config = TrainingConfig(
        adapters_path=tmp_path / "adapters",
        data_path=tmp_path / "data",
        base_model="base-model",
        output_adapter=tmp_path / "output" / "adapter",
        hardware=HardwareConfig(gpu_memory_gb=24, fallback_mode="cpu", precision="8bit"),
    )
    service = LearningService(config)
    service.run(nightly=False)
    adapters = list((tmp_path / "adapters").glob("**/metadata.json"))
    assert adapters

