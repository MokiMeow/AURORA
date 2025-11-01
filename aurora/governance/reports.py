"""Governance reporting utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class GovernanceReport:
    output_path: Path
    content: str


@dataclass(slots=True)
class WeeklyReport(GovernanceReport):
    """Tagged type for weekly reports."""


def generate_weekly_report(metrics_csv: Path, dashboard_html: Path) -> WeeklyReport:
    output = Path("docs/reports/weekly_governance.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    content = f"# Weekly Governance Report\n\nMetrics CSV: {metrics_csv}\nDashboard: {dashboard_html}\n"
    output.write_text(content, encoding="utf-8")
    return WeeklyReport(output_path=output, content=content)


def generate_monthly_report(metrics_csv: Path, incidents_csv: Path) -> GovernanceReport:
    output = Path("docs/reports/monthly_overview.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "# Monthly Governance Overview\n\n"
        f"- Metrics CSV: {metrics_csv}\n"
        f"- Incident Log: {incidents_csv}\n"
    )
    output.write_text(content, encoding="utf-8")
    return GovernanceReport(output_path=output, content=content)


def generate_governance_summary(bundle_path: Path) -> GovernanceReport:
    output = Path("docs/reports/governance_bundle_summary.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    content = f"# Governance Bundle Summary\n\nBundle: {bundle_path}\n"
    output.write_text(content, encoding="utf-8")
    return GovernanceReport(output_path=output, content=content)


def generate_training_report(training_log: Path, adapters_path: Path) -> GovernanceReport:
    output = Path("docs/reports/training_status.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "# Training Status Report\n\n"
        f"- Training log: {training_log}\n"
        f"- Adapter inventory: {adapters_path}\n"
    )
    output.write_text(content, encoding="utf-8")
    return GovernanceReport(output_path=output, content=content)


__all__ = [
    "GovernanceReport",
    "WeeklyReport",
    "generate_weekly_report",
    "generate_monthly_report",
    "generate_governance_summary",
    "generate_training_report",
]
