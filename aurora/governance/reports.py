"""Governance reporting utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class WeeklyReport:
    output_path: Path
    content: str


def generate_weekly_report(metrics_csv: Path, dashboard_html: Path) -> WeeklyReport:
    output = Path("docs/reports/weekly_governance.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    content = f"# Weekly Governance Report\n\nMetrics CSV: {metrics_csv}\nDashboard: {dashboard_html}\n"
    output.write_text(content, encoding="utf-8")
    return WeeklyReport(output_path=output, content=content)

