"""Tests for evaluation analytics utilities."""

import json
from pathlib import Path

from aurora.eval.analytics import export_metrics_csv, load_metrics


def test_load_metrics(tmp_path: Path):
    metrics_file = tmp_path / "lite_metrics.json"
    metrics_file.write_text(
        json.dumps({"suite": "lite", "success_rate": 0.7}), encoding="utf-8"
    )
    df = load_metrics(tmp_path)
    assert not df.empty
    assert df.iloc[0]["suite"] == "lite"


def test_export_metrics_csv(tmp_path: Path):
    metrics_file = tmp_path / "lite_metrics.json"
    metrics_file.write_text(
        json.dumps({"suite": "lite", "success_rate": 0.7}), encoding="utf-8"
    )
    output_csv = tmp_path / "out" / "metrics.csv"
    export_metrics_csv(tmp_path, output_csv)
    assert output_csv.exists()

