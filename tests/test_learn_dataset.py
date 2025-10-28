"""Tests for dataset preparation and bias analysis."""

import json
from pathlib import Path

import pytest

from aurora.learn.config import DatasetConfig
from aurora.learn.dataset import (
    CuratedDataset,
    DatasetError,
    TrainingSample,
    compute_bias_score,
    load_training_dataset,
    load_training_samples,
)


def _write_records(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")


def test_load_training_dataset_filters_and_stratifies(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    records = [
        {"context": {"task": "fix bug"}, "edit": {"summary": "patch"}, "reward": 1.2},
        {"context": {"task": "feature"}, "edit": {"summary": "ship feature"}, "reward": 0.6},
        {"context": {"task": "doc"}, "edit": {"summary": "update docs"}, "reward": 0.3},
        {"context": {"task": "reject"}, "edit": {"summary": "secret ops"}, "reward": 0.9},
    ]
    _write_records(log, records)
    config = DatasetConfig(
        path=log,
        sample_size=3,
        min_reward=0.2,
        stratify_by=("reward", "length"),
        reject_keywords=("secret",),
        augmentations=(),
        balance_labels=True,
        holdout_fraction=0.33,
        max_group_size=2,
    )
    dataset = load_training_dataset(config)
    assert isinstance(dataset, CuratedDataset)
    assert len(dataset.train) >= 1
    assert all(sample.reward >= 0.2 for sample in dataset.train)
    assert all("secret" not in sample.prompt for sample in dataset.train)
    assert len(dataset.holdout) == 1


def test_load_training_dataset_applies_augmentations(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    records = [
        {"context": {"task": f"task-{idx}"}, "edit": {"summary": "patch"}, "reward": 1.0}
        for idx in range(2)
    ]
    _write_records(log, records)
    config = DatasetConfig(
        path=log,
        sample_size=10,
        min_reward=0.0,
        stratify_by=("reward",),
        reject_keywords=(),
        augmentations=("prompt_noise", "completion_shuffle"),
        balance_labels=False,
        holdout_fraction=0.0,
        max_group_size=10,
    )
    dataset = load_training_dataset(config)
    assert len(dataset.train) > len(records)
    assert any(sample.metadata.get("augmentation") for sample in dataset.train)


def test_load_training_samples_backward_compatibility(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    records = [
        {"context": {"task": f"task-{idx}"}, "edit": {"summary": "patch"}, "reward": 0.5}
        for idx in range(5)
    ]
    _write_records(log, records)
    samples = load_training_samples(log, min_reward=0.0, sample_size=2)
    assert len(samples) == 2


def test_load_training_dataset_error_when_empty(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    log.write_text("", encoding="utf-8")
    config = DatasetConfig(
        path=log,
        sample_size=10,
        min_reward=0.0,
        stratify_by=(),
        reject_keywords=(),
        augmentations=(),
        balance_labels=False,
        holdout_fraction=0.0,
        max_group_size=10,
    )
    with pytest.raises(DatasetError):
        load_training_dataset(config)


def test_compute_bias_score_detects_keywords():
    samples = [
        TrainingSample(prompt="Fix issue", completion="Update logic", reward=0.4, metadata={}),
        TrainingSample(prompt="She handles auth", completion="Refine checks", reward=0.6, metadata={}),
    ]
    score = compute_bias_score(samples)
    assert score > 0


def test_compute_bias_score_zero_without_keywords():
    samples = [
        TrainingSample(prompt="Fix issue", completion="Update logic", reward=0.4, metadata={}),
        TrainingSample(prompt="Improve docs", completion="Add examples", reward=0.6, metadata={}),
    ]
    score = compute_bias_score(samples)
    assert score == 0
