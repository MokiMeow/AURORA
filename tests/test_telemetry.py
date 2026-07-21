"""Tests for local telemetry primitives."""

from aurora.telemetry.metrics import MetricsEmitter


def test_metrics_server_starts_once_per_port(monkeypatch) -> None:
    calls: list[int] = []
    port = 19464
    MetricsEmitter._started_ports.discard(port)
    monkeypatch.setattr("aurora.telemetry.metrics.start_http_server", calls.append)

    MetricsEmitter(started=True, port=port)
    MetricsEmitter(started=True, port=port)

    assert calls == [port]
    MetricsEmitter._started_ports.discard(port)
