"""Tests for evaluation metric comparison."""

import json
from pathlib import Path

from aurora.eval.compare import compare_metrics


def test_compare_metrics_numeric(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps({"success_rate": 0.5, "suite": "lite"}), encoding="utf-8")
    b.write_text(json.dumps({"success_rate": 0.7, "suite": "lite"}), encoding="utf-8")
    diff = compare_metrics(a, b)
    delta = {entry["metric"]: entry["delta"] for entry in diff if entry["delta"] is not None}
    assert delta["success_rate"] == 0.19999999999999996


def test_compare_metrics_handles_missing(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps({"metric": 1}), encoding="utf-8")
    b.write_text(json.dumps({"metric": 1, "new_metric": "ok"}), encoding="utf-8")
    diff = compare_metrics(a, b)
    metrics = {entry["metric"]: (entry["run_a"], entry["run_b"]) for entry in diff}
    assert metrics["new_metric"] == (None, "ok")
