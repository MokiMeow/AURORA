"""Indexing service responsible for building the repo intelligence layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class IndexJobConfig:
    """Configuration for a repository indexing job."""

    root: Path
    full: bool = False
    incremental: bool = False

    def validate(self) -> None:
        if self.full and self.incremental:
            msg = "Index job cannot be both full and incremental."
            raise ValueError(msg)
        if not self.full and not self.incremental:
            msg = "Index job must be either full or incremental."
            raise ValueError(msg)


class IndexerService:
    """High-level interface for coordinating indexing subsystems."""

    def __init__(self, observers: Iterable[object] | None = None) -> None:
        self._observers = list(observers or [])

    def run(self, config: IndexJobConfig) -> None:
        config.validate()
        self._notify("start", config)
        try:
            # Placeholder for actual tree-sitter, graph, embedding orchestration.
            self._perform_index(config)
        except Exception as exc:  # pragma: no cover - structured handling later
            self._notify("error", config, exc)
            raise
        else:
            self._notify("complete", config)

    def _perform_index(self, config: IndexJobConfig) -> None:
        # TODO: Implement orchestration once subsystems are available.
        return None

    def _notify(self, event: str, config: IndexJobConfig, error: Exception | None = None) -> None:
        for observer in self._observers:
            handler = getattr(observer, "on_index_event", None)
            if callable(handler):
                handler(event=event, config=config, error=error)

