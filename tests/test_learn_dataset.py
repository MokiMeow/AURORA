"""Tests for dataset preparation and bias analysis."""

import json
from pathlib import Path

import pytest

from aurora.learn.dataset import (
    load_training_samples,
    compute_bias_score,
    DatasetError,
    TrainingSample,
)


def test_load_training_samples_filters_by_reward(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    records = [
        {"context": {"task": "fix bug"}, "edit": {"summary": "patch"}, "reward": 0.5},
        {"context": {"task": "feature"}, "edit": {"summary": "add"}, "reward": -0.1},
    ]
    log.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
    samples = load_training_samples(log, min_reward=0.0, sample_size=10)
    assert len(samples) == 1
    assert samples[0].prompt == "fix bug"


def test_load_training_samples_respects_sample_size(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    records = [
        {"context": {"task": f"task-{idx}"}, "edit": {"summary": "patch"}, "reward": 0.5}
        for idx in range(5)
    ]
    log.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
    samples = load_training_samples(log, min_reward=0.0, sample_size=2)
    assert len(samples) == 2


def test_load_training_samples_error_when_empty(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    log.write_text("", encoding="utf-8")
    with pytest.raises(DatasetError):
        load_training_samples(log, min_reward=0.0, sample_size=5)


def test_compute_bias_score_detects_keywords():
    samples = [
        TrainingSample(prompt="Fix issue", completion="Update logic", reward=0.4),
        TrainingSample(prompt="She handles auth", completion="Refine checks", reward=0.6),
    ]
    score = compute_bias_score(samples)
    assert score > 0


def test_compute_bias_score_zero_without_keywords():
    samples = [
        TrainingSample(prompt="Fix issue", completion="Update logic", reward=0.4),
        TrainingSample(prompt="Improve docs", completion="Add examples", reward=0.6),
    ]
    score = compute_bias_score(samples)
    assert score == 0

