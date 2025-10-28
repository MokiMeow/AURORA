"""Utilities for preparing Filtered-SFT datasets from experience logs."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence, Tuple

from .config import DatasetConfig


class DatasetError(RuntimeError):
    """Raised when the dataset cannot be prepared."""


BIAS_KEYWORDS = {
    "gender": [" he ", " she ", " him ", " her "],
    "ethnicity": ["asian", "african", "hispanic", "caucasian"],
    "age": ["elderly", "youth", "teen", "senior"],
}


@dataclass(slots=True)
class TrainingSample:
    prompt: str
    completion: str
    reward: float
    metadata: dict


@dataclass(slots=True)
class CuratedDataset:
    train: list[TrainingSample]
    holdout: list[TrainingSample]


def _iter_records(path: Path) -> Iterator[dict]:
    if not path.exists():
        raise DatasetError(f"Experience log not found at {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:  # pragma: no cover - logged via caller
                raise DatasetError(f"Invalid JSON in experience log: {exc}") from exc


def _build_sample(record: dict) -> TrainingSample:
    context = record.get("context", {})
    edit = record.get("edit", {})
    prompt = context.get("task") or context.get("description") or json.dumps(context)
    completion = edit.get("diff") or edit.get("summary") or json.dumps(edit)
    return TrainingSample(
        prompt=prompt,
        completion=completion,
        reward=float(record.get("reward", 0.0)),
        metadata={
            "task": context.get("task"),
            "domain": context.get("domain") or context.get("language"),
            "length": len(prompt) + len(completion),
            "bias": record.get("telemetry", {}).get("bias"),
            "tags": record.get("metadata", {}).get("tags"),
        },
    )


def _reject_keywords(samples: List[TrainingSample], keywords: Sequence[str]) -> List[TrainingSample]:
    if not keywords:
        return samples
    rejected = []
    for sample in samples:
        text = f"{sample.prompt} {sample.completion}".lower()
        if any(keyword.lower() in text for keyword in keywords):
            continue
        rejected.append(sample)
    return rejected


def _augment_samples(samples: List[TrainingSample], augmentations: Sequence[str]) -> List[TrainingSample]:
    if not augmentations:
        return samples
    augmented = samples.copy()
    for augmentation in augmentations:
        if augmentation == "prompt_noise":
            for sample in samples:
                noisy_prompt = f"{sample.prompt}\n# context: generated augmentation"
                augmented.append(
                    TrainingSample(
                        prompt=noisy_prompt,
                        completion=sample.completion,
                        reward=sample.reward * 0.95,
                        metadata={**sample.metadata, "augmentation": augmentation},
                    )
                )
        elif augmentation == "completion_shuffle":
            shuffled = samples.copy()
            random.shuffle(shuffled)
            for base, shuffled_sample in zip(samples, shuffled):
                augmented.append(
                    TrainingSample(
                        prompt=base.prompt,
                        completion=shuffled_sample.completion,
                        reward=(base.reward + shuffled_sample.reward) / 2,
                        metadata={**base.metadata, "augmentation": augmentation},
                    )
                )
    return augmented


def _bucket_key(sample: TrainingSample, strategy: str) -> str:
    strategy = strategy.lower()
    if strategy == "reward":
        if sample.reward >= 1.0:
            return "reward_high"
        if sample.reward >= 0.5:
            return "reward_medium"
        return "reward_low"
    if strategy == "length":
        length = sample.metadata.get("length", len(sample.prompt) + len(sample.completion))
        if length > 800:
            return "length_long"
        if length > 200:
            return "length_medium"
        return "length_short"
    if strategy == "domain":
        return f"domain_{sample.metadata.get('domain') or 'unknown'}"
    return "default"


def _stratify_samples(
    samples: List[TrainingSample],
    strategies: Sequence[str],
    balance: bool,
    max_group_size: int,
    target_size: int,
) -> List[TrainingSample]:
    if not strategies:
        strategies = ("default",)
    buckets: dict[Tuple[str, ...], list[TrainingSample]] = defaultdict(list)
    for sample in samples:
        key = tuple(_bucket_key(sample, strategy) for strategy in strategies)
        buckets[key].append(sample)
    curated: list[TrainingSample] = []
    if balance:
        per_bucket = min(max_group_size, max(1, target_size // max(1, len(buckets))))
        for bucket_samples in buckets.values():
            random.shuffle(bucket_samples)
            curated.extend(bucket_samples[:per_bucket])
    else:
        for bucket_samples in buckets.values():
            random.shuffle(bucket_samples)
            curated.extend(bucket_samples)
    random.shuffle(curated)
    if target_size and len(curated) > target_size:
        curated = curated[:target_size]
    return curated


def load_training_dataset(config: DatasetConfig) -> CuratedDataset:
    records = [record for record in _iter_records(config.path) if record.get("reward", 0) >= config.min_reward]
    if not records:
        raise DatasetError("No suitable experience records found for training")

    samples = [_build_sample(record) for record in records]
    samples = _reject_keywords(samples, config.reject_keywords)
    if not samples:
        raise DatasetError("All samples rejected by keyword filters")

    samples = _augment_samples(samples, config.augmentations)
    curated = _stratify_samples(
        samples,
        strategies=config.stratify_by,
        balance=config.balance_labels,
        max_group_size=config.max_group_size,
        target_size=config.sample_size,
    )
    if not curated:
        raise DatasetError("Dataset curation produced zero samples")

    holdout_count = int(len(curated) * config.holdout_fraction)
    if config.holdout_fraction == 0:
        holdout_count = 0
    else:
        holdout_count = min(max(holdout_count, 1 if len(curated) > 1 else 0), len(curated))
    holdout = curated[:holdout_count]
    train = curated[holdout_count:]
    if not train:
        raise DatasetError("Holdout split consumed all samples")
    return CuratedDataset(train=train, holdout=holdout)


def compute_bias_score(samples: Iterable[TrainingSample]) -> float:
    """Compute a heuristic bias score based on keyword prevalence."""

    total = 0
    hits = 0
    for sample in samples:
        text = f"{sample.prompt} {sample.completion}".lower()
        total += 1
        for keywords in BIAS_KEYWORDS.values():
            if any(keyword in text or keyword.strip() in text for keyword in keywords):
                hits += 1
                break
    if total == 0:
        return 0.0
    return hits / total


def save_bias_report(report_path: Path, bias_score: float, sample_count: int) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {"bias_score": bias_score, "sample_count": sample_count}
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def load_training_samples(log_path: Path, min_reward: float, sample_size: int) -> list[TrainingSample]:
    """Backward-compatible helper returning curated training samples."""

    config = DatasetConfig(
        path=log_path,
        sample_size=sample_size,
        min_reward=min_reward,
        stratify_by=("reward",),
        reject_keywords=(),
        augmentations=(),
        balance_labels=False,
        holdout_fraction=0.0,
        max_group_size=sample_size or 512,
    )
    curated = load_training_dataset(config)
    return curated.train


