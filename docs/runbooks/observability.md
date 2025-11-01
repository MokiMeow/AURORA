# Observability & Telemetry Operations

## Prometheus / Metrics
- Ports exposed via `configs/telemetry.yaml` (`port: 9464`).
- Metrics emitted by `aurora.telemetry.metrics.MetricsEmitter` for evaluations and rewards.
- To restart exporter locally: `aurora-se telemetry`.

## OpenTelemetry
- Endpoint configured via `otel.endpoint`.
- Spans delivered using OTLP gRPC exporter.
- Ensure collector is running (`docker compose up otel-collector`).

## PDCA Logs
- Location: `telemetry/pdca.jsonl`.
- Export using `aurora-se telemetry --export`.
- Retain logs for 90 days per governance policy.

## Error Logging
- Structured errors appended to `telemetry/errors.jsonl`.
- Categorize incidents by `category` field; escalate security events immediately.


