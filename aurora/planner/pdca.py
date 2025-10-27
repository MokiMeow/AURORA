"""PDCA telemetry helpers for planner."""

from __future__ import annotations

from pathlib import Path

from aurora.telemetry.pdca import PDCAEntry as TelemetryPDCAEntry

PDCA_LOG = Path("telemetry/pdca.jsonl")


def PDCAEntry(phase: str, event: str, payload: dict) -> None:
    """Proxy to telemetry PDCA writer for backward compatibility."""
    TelemetryPDCAEntry(phase=phase, event=event, payload=payload)

