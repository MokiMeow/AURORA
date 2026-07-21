"""Tests for evaluation analytics utilities."""

import json
from pathlib import Path

from aurora.eval.analytics import export_metrics_csv, load_metrics, generate_dashboard, diff_sbom


def _write_metric(path: Path, suite: str) -> None:
    path.write_text(json.dumps({"suite": suite, "success_rate": 0.7}), encoding="utf-8")


def test_load_metrics(tmp_path: Path):
    metrics_file = tmp_path / "lite_metrics.json"
    _write_metric(metrics_file, "lite")
    df = load_metrics(tmp_path)
    assert not df.empty
    assert df.iloc[0]["suite"] == "lite"


def test_export_metrics_csv(tmp_path: Path):
    metrics_file = tmp_path / "lite_metrics.json"
    _write_metric(metrics_file, "lite")
    output_csv = tmp_path / "out" / "metrics.csv"
    export_metrics_csv(tmp_path, output_csv)
    assert output_csv.exists()


def test_export_metrics_csv_neutralizes_spreadsheet_formulas(tmp_path: Path):
    metrics_file = tmp_path / "unsafe_metrics.json"
    metrics_file.write_text(
        json.dumps({"suite": "=1+1", "success_rate": 1.0}),
        encoding="utf-8",
    )
    output_csv = tmp_path / "out" / "metrics.csv"

    export_metrics_csv(tmp_path, output_csv)

    assert "'=1+1" in output_csv.read_text(encoding="utf-8")


def test_generate_dashboard(tmp_path: Path):
    metrics_file = tmp_path / "lite_metrics.json"
    _write_metric(metrics_file, "lite")
    dashboard_path = tmp_path / "dash" / "index.html"
    generate_dashboard(tmp_path, dashboard_path)
    assert dashboard_path.exists()


def test_diff_sbom(tmp_path: Path):
    prev = tmp_path / "prev.json"
    curr = tmp_path / "curr.json"
    prev.write_text("prev", encoding="utf-8")
    curr.write_text("curr", encoding="utf-8")
    output = tmp_path / "diff.json"
    diff_sbom(prev, curr, output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["previous"] == "prev"
    assert payload["current"] == "curr"

