"""Analytics utilities for evaluation results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import plotly.express as px


@dataclass(slots=True)
class AnalyticsConfig:
    results_dir: Path
    output_csv: Path
    dashboard_html: Path


def load_metrics(results_dir: Path) -> pd.DataFrame:
    records = []
    for path in results_dir.glob("*_metrics.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        records.append(payload)
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if "run_id" not in df.columns:
        df["run_id"] = df.index.astype(str)
    return df


def export_metrics_csv(results_dir: Path, output_csv: Path) -> None:
    df = load_metrics(results_dir)
    if df.empty:
        output_csv.write_text("", encoding="utf-8")
        return
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)


def generate_dashboard(results_dir: Path, dashboard_html: Path) -> None:
    df = load_metrics(results_dir)
    if df.empty:
        dashboard_html.parent.mkdir(parents=True, exist_ok=True)
        dashboard_html.write_text("<p>No evaluation runs yet.</p>", encoding="utf-8")
        return
    fig = px.bar(df, x="run_id", y="success_rate", color="suite", title="SWE-Bench Success Rates")
    dashboard_html.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(dashboard_html)


def diff_sbom(prev: Path | None, current: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "previous": prev.read_text(encoding="utf-8") if prev and prev.exists() else None,
        "current": current.read_text(encoding="utf-8") if current.exists() else None,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

