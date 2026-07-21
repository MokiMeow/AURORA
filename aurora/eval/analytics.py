"""Analytics utilities for evaluation results."""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _safe_csv_cell(value: object) -> object:
    """Keep spreadsheet programs from interpreting untrusted text as formulas."""

    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


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
    if "success_rate" not in df.columns and "exit_code" in df.columns:
        df["success_rate"] = df["exit_code"].apply(lambda code: 1.0 if code == 0 else 0.0)
    return df.sort_values("run_id")


def export_metrics_csv(results_dir: Path, output_csv: Path) -> None:
    df = load_metrics(results_dir)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        output_csv.write_text("", encoding="utf-8")
        return
    safe_df = df.copy()
    for column in safe_df.select_dtypes(include=["object", "string"]).columns:
        safe_df[column] = safe_df[column].map(_safe_csv_cell)
    safe_df.to_csv(output_csv, index=False)


def _failure_taxonomy(df: pd.DataFrame) -> pd.Series:
    if "failure_reason" in df.columns:
        reasons = df["failure_reason"].fillna("unknown")
        return reasons.value_counts()
    if "exit_code" in df.columns:
        failures = df[df["exit_code"] != 0]
    else:
        failures = pd.DataFrame()
    if failures.empty:
        return pd.Series(dtype=int)
    return failures.groupby("suite").size()


def _latency_series(df: pd.DataFrame) -> pd.Series:
    if "latency" in df.columns:
        return df["latency"].astype(float)
    if "latency_seconds" in df.columns:
        return df["latency_seconds"].astype(float)
    return df.get("duration_seconds", pd.Series(dtype=float))


def generate_dashboard(results_dir: Path, dashboard_html: Path) -> None:
    df = load_metrics(results_dir)
    dashboard_html.parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        dashboard_html.write_text("<p>No evaluation runs yet.</p>", encoding="utf-8")
        return

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("Success Rate", "Latency (seconds)"),
    )
    fig.add_trace(
        go.Scatter(
            x=df["run_id"],
            y=df["success_rate"],
            mode="lines+markers",
            name="Success Rate",
            line=dict(color="#2ca02c"),
        ),
        row=1,
        col=1,
    )
    latency_series = _latency_series(df)
    if len(latency_series) > 0:
        fig.add_trace(
            go.Bar(
                x=df["run_id"],
                y=latency_series,
                name="Latency (s)",
                marker_color="#1f77b4",
            ),
            row=2,
            col=1,
        )
    fig.update_layout(
        title="Evaluation Trend",
        height=600,
        showlegend=True,
        margin=dict(l=40, r=40, t=60, b=40),
    )

    failures = _failure_taxonomy(df)
    if not failures.empty:
        heatmap = go.Figure(
            data=[
                go.Heatmap(
                    z=[failures.values.tolist()],
                    x=failures.index.tolist(),
                    y=["failures"],
                    colorscale="Reds",
                    showscale=True,
                    name="Failure taxonomy",
                )
            ]
        )
        heatmap.update_layout(height=300, margin=dict(l=40, r=40, t=40, b=40))
        figs = [fig, heatmap]
    else:
        figs = [fig]

    html_parts = [f.to_html(full_html=False, include_plotlyjs="cdn") for f in figs]
    dashboard_html.write_text("\n".join(html_parts), encoding="utf-8")


def diff_sbom(prev: Path | None, current: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "previous": prev.read_text(encoding="utf-8") if prev and prev.exists() else None,
        "current": current.read_text(encoding="utf-8") if current.exists() else None,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
