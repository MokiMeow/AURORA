"""Production-ready indexing service coordinating repo intelligence."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import IndexerConfig
from .embedding import EmbeddingStore
from .store import GraphStore
from .tree import TreeSitterParser

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class IndexJobConfig:
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
    def __init__(
        self,
        config: IndexerConfig,
        graph_store: GraphStore,
        parser: TreeSitterParser,
        embedding_store: EmbeddingStore,
        observers: Iterable[object] | None = None,
    ) -> None:
        self._config = config
        self._graph_store = graph_store
        self._parser = parser
        self._embedding_store = embedding_store
        self._observers = list(observers or [])

    def run(self, job: IndexJobConfig) -> None:
        job.validate()
        self._notify("start", job)
        LOGGER.info(
            "Starting index job",
            extra={"root": str(job.root), "full": job.full, "incremental": job.incremental},
        )
        try:
            self._perform_index(job)
        except Exception as exc:  # pragma: no cover
            self._notify("error", job, exc)
            LOGGER.exception("Index job failed: %s", exc)
            raise
        else:
            self._notify("complete", job)
            LOGGER.info("Index job completed", extra={"root": str(job.root)})

    def _perform_index(self, job: IndexJobConfig) -> None:
        sources = self._parser.scan_repository(self._config.root)
        parsed_units = list(self._parser.parse_sources(sources))
        changed_paths = self._graph_store.store_units(parsed_units, full=job.full)
        if not changed_paths:
            LOGGER.info("No changes detected; skipping embedding indexing")
            return
        embeddings = [
            self._embedding_store.embed_content(str(unit.path), unit.content)
            for unit in parsed_units
            if str(unit.path) in changed_paths
        ]
        self._embedding_store.index(embeddings)

    def _notify(self, event: str, job: IndexJobConfig, error: Exception | None = None) -> None:
        for observer in self._observers:
            handler = getattr(observer, "on_index_event", None)
            if callable(handler):
                handler(event=event, job=job, error=error)

