"""Explainability and reporting helpers for the reward engine."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from string import Template
from typing import Any, Iterable, List

DEFAULT_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Aurora-SE Reward Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; }
    table { border-collapse: collapse; margin-bottom: 16px; }
    th, td { border: 1px solid #ddd; padding: 6px 12px; text-align: left; }
    th { background: #f3f4f6; }
    .success { color: #067647; font-weight: 600; }
    .failure { color: #b42318; font-weight: 600; }
  </style>
</head>
<body>
  <h1>Aurora-SE Reward Report</h1>
  <p><strong>Timestamp:</strong> $timestamp</p>
  <p><strong>Reward:</strong> $reward</p>
  <p><strong>Status:</strong> <span class="$status_class">$status_label</span></p>
  <h2>Components</h2>
  <table>
    <tbody>
      $components_table
    </tbody>
  </table>
  <h2>Penalties</h2>
  <table>
    <tbody>
      $penalties_table
    </tbody>
  </table>
  <h2>Metrics</h2>
  <table>
    <tbody>
      $metrics_table
    </tbody>
  </table>
  <h2>Policy Reasons</h2>
  <ul>
    $reasons_list
  </ul>
  $timeline_section
</body>
</html>
"""


@dataclass(slots=True)
class RewardObservation:
    reward: float
    components: dict[str, float]
    penalties: dict[str, float]
    metrics: dict[str, Any]
    success: bool
    reasons: List[str]
    metadata: dict[str, Any]


class RewardReportWriter:
    def __init__(
        self,
        store_path: Path,
        formats: Iterable[str] = ("json",),
        keep_last: int = 50,
        enable_timeline: bool = True,
        html_template: Path | None = None,
        history_filename: str = "reward_history.jsonl",
        trend_filename: str = "reward_trend.html",
    ) -> None:
        self._store_path = store_path
        self._store_path.mkdir(parents=True, exist_ok=True)
        self._formats = tuple(str(fmt).lower() for fmt in formats)
        self._keep_last = keep_last
        self._enable_timeline = enable_timeline
        self._html_template = html_template
        self._history_path = self._store_path / history_filename
        self._trend_path = self._store_path / trend_filename

    def write(self, observation: RewardObservation) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        record = {
            "timestamp": timestamp,
            "reward": observation.reward,
            "components": observation.components,
            "penalties": observation.penalties,
            "metrics": observation.metrics,
            "success": observation.success,
            "reasons": observation.reasons,
            "metadata": observation.metadata,
        }
        history = self._update_history(record)

        if "json" in self._formats:
            self._write_json(record)
        if "html" in self._formats:
            self._write_html(record, history)

    def _write_json(self, record: dict[str, Any]) -> None:
        latest_path = self._store_path / "latest_reward.json"
        latest_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    def _write_html(self, record: dict[str, Any], history: List[dict[str, Any]]) -> None:
        template_str = DEFAULT_TEMPLATE
        if self._html_template and self._html_template.exists():
            template_str = self._html_template.read_text(encoding="utf-8")

        template = Template(template_str)
        html = template.safe_substitute(
            timestamp=escape(str(record["timestamp"])),
            reward=f"{record['reward']:.3f}",
            status_class="success" if record["success"] else "failure",
            status_label="Accepted" if record["success"] else "Rejected",
            components_table=self._rows_from_mapping(record["components"]),
            penalties_table=self._rows_from_mapping(record["penalties"] or {"bias": 0.0}),
            metrics_table=self._rows_from_mapping(record["metrics"]),
            reasons_list=self._reasons_list(record["reasons"]),
            timeline_section=self._timeline_section(history) if self._enable_timeline else "",
        )
        (self._store_path / "latest_reward.html").write_text(html, encoding="utf-8")
        if self._enable_timeline:
            self._trend_path.write_text(self._timeline_page(history), encoding="utf-8")

    def _rows_from_mapping(self, mapping: dict[str, Any]) -> str:
        if not mapping:
            return "<tr><td colspan='2'>No data</td></tr>"
        rows = []
        for key, value in mapping.items():
            if isinstance(value, float):
                display = f"{value:.3f}"
            else:
                display = str(value)
            rows.append(
                f"<tr><th>{escape(str(key))}</th><td>{escape(display)}</td></tr>"
            )
        return "\n      ".join(rows)

    @staticmethod
    def _reasons_list(reasons: Iterable[str]) -> str:
        if not reasons:
            return "<li>No policy notes</li>"
        return "\n    ".join(f"<li>{escape(str(reason))}</li>" for reason in reasons)

    def _timeline_section(self, history: List[dict[str, Any]]) -> str:
        items = "\n    ".join(
            f"<li>{escape(str(entry['timestamp']))} &mdash; "
            f"reward={entry['reward']:.3f} success={entry['success']}</li>"
            for entry in history[-10:]
        )
        return f"<h2>Recent Trend</h2><ul>{items}</ul>"

    def _timeline_page(self, history: List[dict[str, Any]]) -> str:
        rows = "\n".join(
            "<tr>"
            f"<td>{escape(str(entry['timestamp']))}</td>"
            f"<td>{entry['reward']:.3f}</td>"
            f"<td>{'Yes' if entry['success'] else 'No'}</td>"
            "</tr>"
            for entry in history[-self._keep_last :]
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Aurora-SE Reward Trend</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 12px; text-align: left; }}
    th {{ background: #f9fafb; }}
  </style>
</head>
<body>
  <h1>Reward Trend</h1>
  <table>
    <thead>
      <tr><th>Timestamp</th><th>Reward</th><th>Success</th></tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
  <p>Generated at {datetime.now(timezone.utc).isoformat()}</p>
</body>
</html>
"""

    def _update_history(self, record: dict[str, Any]) -> List[dict[str, Any]]:
        records: List[dict[str, Any]] = []
        if self._history_path.exists():
            existing = self._history_path.read_text(encoding="utf-8").splitlines()
            for line in existing:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        records.append(record)
        records = records[-self._keep_last :]
        with self._history_path.open("w", encoding="utf-8") as handle:
            for entry in records:
                handle.write(json.dumps(entry) + "\n")
        return records


__all__ = ["RewardObservation", "RewardReportWriter"]
