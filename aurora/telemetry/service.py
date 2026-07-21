"""Telemetry configuration and dashboard metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class TelemetryConfig:
    endpoint: str
    service_name: str
    environment: str
    collector_config: Path | None
    prometheus_port: int
    prometheus_targets: tuple[str, ...]
    prometheus_scrape_interval: str
    log_file: Path
    log_retention_days: int
    log_aggregation_provider: str | None
    log_aggregation_bucket: str | None
    dashboard_url: str
    dashboard_uid: str | None
    alert_rules: Path | None


class TelemetryService:
    """Resolve telemetry configuration without starting background services."""

    def __init__(self, config: TelemetryConfig) -> None:
        self.config = config

    @classmethod
    def from_config(cls, path: Path) -> "TelemetryService":
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        otel = data.get("otel", {})
        prometheus = data.get("prometheus", {})
        logging = data.get("logging", {})
        dashboard = data.get("grafana", data.get("dashboard", {}))
        aggregation = logging.get("aggregation", {})
        alerting = data.get("alerting", {})

        collector = otel.get("collector_config")
        alert_rules = alerting.get("rules")
        config = TelemetryConfig(
            endpoint=str(otel.get("endpoint", "http://localhost:4317")),
            service_name=str(otel.get("service_name", "aurora-se")),
            environment=str(otel.get("environment", "local")),
            collector_config=Path(collector) if collector else None,
            prometheus_port=int(prometheus.get("port", 9464)),
            prometheus_targets=tuple(str(item) for item in prometheus.get("targets", ())),
            prometheus_scrape_interval=str(prometheus.get("scrape_interval", "15s")),
            log_file=Path(logging.get("file", "telemetry/pdca.jsonl")),
            log_retention_days=int(logging.get("retention_days", 7)),
            log_aggregation_provider=aggregation.get("provider"),
            log_aggregation_bucket=aggregation.get("bucket"),
            dashboard_url=str(dashboard.get("url", "http://localhost:3000")),
            dashboard_uid=dashboard.get("dashboard_uid"),
            alert_rules=Path(alert_rules) if alert_rules else None,
        )
        return cls(config)

    def dashboard_links(self) -> dict[str, str]:
        local = f"http://localhost:{self.config.prometheus_port}/metrics"
        remote = self.config.dashboard_url.rstrip("/")
        if self.config.dashboard_uid and "/d/" not in remote:
            remote = f"{remote}/d/{self.config.dashboard_uid}"
        return {"service": local, "grafana": remote}

    def alerting_metadata(self) -> dict[str, str | None]:
        return {"rules": str(self.config.alert_rules) if self.config.alert_rules else None}


__all__ = ["TelemetryConfig", "TelemetryService"]
