# Telemetry Commands

```
aurora-se telemetry init --environment staging
aurora-se telemetry dashboard --remote --export
aurora-se telemetry export --interval 24h
```

- **init** – loads telemetry templates from `configs/telemetry/<env>.yaml` and prepares logging/metrics collectors.
- **dashboard** – prints local or remote Grafana dashboards and can export metadata including retention, alert rules, and collector config.
- **export** – copies telemetry logs, annotating the requested interval in a companion metadata file for audits.

Templates are provided for local, staging, and production environments alongside OTEL collector configurations.
