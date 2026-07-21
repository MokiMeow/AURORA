"""Utilities for comparing evaluation metric files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _load_metrics(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare_metrics(path_a: Path, path_b: Path) -> List[dict[str, Any]]:
    metrics_a = _load_metrics(path_a)
    metrics_b = _load_metrics(path_b)
    keys = sorted(set(metrics_a.keys()) | set(metrics_b.keys()))
    diff: List[dict[str, Any]] = []
    for key in keys:
        value_a = metrics_a.get(key)
        value_b = metrics_b.get(key)
        numeric_a = _as_number(value_a)
        numeric_b = _as_number(value_b)
        delta = numeric_b - numeric_a if numeric_a is not None and numeric_b is not None else None
        diff.append(
            {
                "metric": key,
                "run_a": value_a,
                "run_b": value_b,
                "delta": delta,
            }
        )
    return diff


def _as_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
