
"""Tests for the SFT pipeline."""

import json
from pathlib import Path

from aurora.learn.config import AccelerateConfig, DatasetConfig, HardwareConfig
from aurora.learn.pipeline import SFTPipeline


def test_sft_pipeline_produces_artifacts(tmp_path: Path):
    log_path = tmp_path / "experience.jsonl"
    log_path.write_text(
        "\n".join(
            json.dumps({"context": {"task": f"task-{idx}"}, "edit": {"summary": "patch"}, "reward": 0.8})
            for idx in range(3)
        ),
        encoding="utf-8",
    )
    dataset_config = DatasetConfig(
        path=log_path,
        sample_size=3,
        min_reward=0.0,
        stratify_by=("reward",),
        reject_keywords=(),
        augmentations=(),
        balance_labels=False,
        holdout_fraction=0.33,
        max_group_size=10,
    )
    accelerate = AccelerateConfig(
        mixed_precision="bf16",
        gradient_accumulation_steps=1,
        gradient_checkpointing=False,
        deepspeed_config=None,
        device_map="auto",
        use_int8=False,
        compile_model=False,
    )
    hardware = HardwareConfig(gpu_memory_gb=8, fallback_mode="cpu", precision="8bit", prefer_gpu=False)
    pipeline = SFTPipeline(
        experience_log=log_path,
        base_model="base-model",
        output_path=tmp_path / "output",
        epochs=1,
        learning_rate=0.001,
        dataset_config=dataset_config,
        accelerate=accelerate,
        hardware=hardware,
        regularization_prompts=(),
        simulate=True,
    )
    result = pipeline.run()
    assert result.training_metrics["samples"] >= 2
    assert (result.adapter_path / "training_metrics.json").exists()
    assert result.holdout_metrics["holdout_samples"] == len(result.dataset.holdout)
