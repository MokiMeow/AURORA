"""Prometheus-compatible reward metrics with a no-server default."""

from __future__ import annotations

from threading import Lock
from typing import ClassVar

from prometheus_client import Gauge, start_http_server


class MetricsEmitter:
    """Record process-local metrics and optionally expose them over HTTP."""

    _start_lock: ClassVar[Lock] = Lock()
    _started_ports: ClassVar[set[int]] = set()

    _reward = Gauge(
        "aurora_reward_latest",
        "Latest AURORA reward value by evaluation suite",
        labelnames=("suite",),
    )

    def __init__(self, *, started: bool = False, port: int = 9464) -> None:
        self.started = started
        self.port = port
        if started:
            with self._start_lock:
                if port not in self._started_ports:
                    start_http_server(port)
                    self._started_ports.add(port)

    def record_reward(self, suite: str, reward: float) -> None:
        self._reward.labels(suite=suite).set(float(reward))


__all__ = ["MetricsEmitter"]
