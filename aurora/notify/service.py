"""Notification service for emitting channel events."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import yaml


@dataclass(slots=True)
class NotificationConfig:
    channels: Dict[str, dict]
    log_path: Path


def load_notification_config(path: Path) -> NotificationConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    channels = data.get("channels", {})
    log_path = Path(data.get("log_path", "artifacts/notify/log.jsonl"))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return NotificationConfig(channels=channels, log_path=log_path)


class NotificationService:
    """Persist notifications to a log file for auditability."""

    def __init__(self, config: NotificationConfig) -> None:
        self._config = config

    def send(self, channel: str, message: str, metadata: dict | None = None) -> Path:
        if channel not in self._config.channels:
            raise ValueError(f"Channel '{channel}' not configured.")
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "channel": channel,
            "message": message,
            "metadata": metadata or {},
        }
        with self._config.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
        return self._config.log_path

    @property
    def config(self) -> NotificationConfig:
        return self._config
