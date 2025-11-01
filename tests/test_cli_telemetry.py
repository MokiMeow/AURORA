"""Tests for telemetry CLI."""

import json
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_telemetry_dashboard_export(tmp_path: Path) -> None:
    config = tmp_path / "telemetry.yaml"
    export_path = tmp_path / "dashboard.json"
    config.write_text(
        "otel:\n  endpoint: http://localhost:4317\n  service_name: test\n  environment: local\n"
        "prometheus:\n  port: 9464\n  targets: ['http://localhost:9464/metrics']\n  scrape_interval: 15s\n"
        "logging:\n  level: INFO\n  format: json\n  file: telemetry/test.jsonl\n  retention_days: 7\n"
        "grafana:\n  url: http://localhost:3000\n  dashboard_uid: test\n",
        encoding="utf-8",
    )
    dashboard = runner.invoke(
        app,
        [
            "telemetry",
            "dashboard",
            "--config",
            str(config),
            "--export",
            "--remote",
            "--output",
            str(export_path),
        ],
    )
    assert dashboard.exit_code == 0
    data = json.loads(export_path.read_text(encoding="utf-8"))
    assert data["environment"] == "local"
    assert data["dashboard_grafana"].startswith("http://localhost:3000")


def test_telemetry_export(tmp_path: Path) -> None:
    source = tmp_path / "telemetry.log"
    source.write_text("{}\n{}", encoding="utf-8")
    destination = tmp_path / "out.log"
    result = runner.invoke(
        app,
        [
            "telemetry",
            "export",
            "--source",
            str(source),
            "--destination",
            str(destination),
            "--interval",
            "24h",
        ],
    )
    assert result.exit_code == 0
    meta = destination.with_suffix(destination.suffix + ".meta.json")
    assert destination.exists()
    assert meta.exists()
    meta_payload = json.loads(meta.read_text(encoding="utf-8"))
    assert meta_payload["interval"] == "24h"
