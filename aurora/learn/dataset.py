"""Utilities for preparing Filtered-SFT datasets from experience logs."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List


class DatasetError(RuntimeError):
    """Raised when the dataset cannot be prepared."""


BIAS_KEYWORDS = {
    "gender": ["he ", "she ", "him", "her"],
    "ethnicity": ["asian", "african", "hispanic", "caucasian"],
    "age": ["elderly", "youth", "teen", "senior"],
}


@dataclass(slots=True)
class TrainingSample:
    prompt: str
    completion: str
    reward: float


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


def load_training_samples(log_path: Path, min_reward: float, sample_size: int) -> list[TrainingSample]:
    """Load experience records and select samples meeting reward threshold."""

    records = [record for record in _iter_records(log_path) if record.get("reward", 0) >= min_reward]
    if not records:
        raise DatasetError("No suitable experience records found for training")

    samples: List[TrainingSample] = []
    for record in records:
        context = record.get("context", {})
        edit = record.get("edit", {})
        prompt = context.get("task") or context.get("description") or json.dumps(context)
        completion = edit.get("diff") or edit.get("summary") or json.dumps(edit)
        samples.append(TrainingSample(prompt=prompt, completion=completion, reward=record.get("reward", 0)))

    random.shuffle(samples)
    return samples[: sample_size or len(samples)]


def compute_bias_score(samples: Iterable[TrainingSample]) -> float:
    """Compute a heuristic bias score based on keyword prevalence."""

    total = 0
    hits = 0
    for sample in samples:
        text = f"{sample.prompt} {sample.completion}".lower()
        total += 1
        if any(keyword in text for keywords in BIAS_KEYWORDS.values() for keyword in keywords):
            hits += 1
    if total == 0:
        return 0.0
    return hits / total


def save_bias_report(report_path: Path, bias_score: float, sample_count: int) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {"bias_score": bias_score, "sample_count": sample_count}
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


