"""Analytics utilities for evaluation results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass(slots=True)
class AnalyticsConfig:
    results_dir: Path
    output_csv: Path


def load_metrics(results_dir: Path) -> pd.DataFrame:
    records = []
    for path in results_dir.glob("*_metrics.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        records.append(payload)
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def export_metrics_csv(results_dir: Path, output_csv: Path) -> None:
    df = load_metrics(results_dir)
    if df.empty:
        output_csv.write_text("", encoding="utf-8")
        return
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)

