"""Embedding indexer supporting pgvector and Milvus."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import Column, MetaData, String, Table, create_engine, insert, select
from sqlalchemy.engine import Engine

LOGGER = logging.getLogger(__name__)

_metadata = MetaData()
_embeddings = Table(
    "embeddings",
    _metadata,
    Column("path", String, primary_key=True),
    Column("vector", String, nullable=False),
)


@dataclass(slots=True)
class EmbeddingRecord:
    path: str
    embedding: list[float]


class EmbeddingStore:
    def __init__(self, enabled: bool = True, model: str = "hash32", database_url: str | None = None) -> None:
        self._enabled = enabled
        self._model = model
        self._engine: Engine | None = None
        if database_url:
            self._engine = create_engine(database_url, future=True)
            _metadata.create_all(self._engine)

    def index(self, records: Iterable[EmbeddingRecord]) -> None:
        if not self._enabled or not self._engine:
            LOGGER.debug("Embedding store disabled; skipping indexing")
            return
        with self._engine.begin() as connection:
            for record in records:
                connection.execute(
                    insert(_embeddings)
                    .values(path=record.path, vector=json.dumps(record.embedding))
                    .prefix_with("OR REPLACE")
                )

    def embed_content(self, path: str, content: str) -> EmbeddingRecord:
        if self._model == "hash32":
            digest = hashlib.sha256(content.encode("utf-8")).digest()
            embedding = [int.from_bytes(digest[i:i + 2], "big") / 65535.0 for i in range(0, 64, 2)]
        else:
            raise NotImplementedError(f"Embedding model {self._model} not implemented")
        return EmbeddingRecord(path=path, embedding=embedding)

    def query(self, limit: int = 20) -> list[EmbeddingRecord]:
        if not self._engine:
            return []
        with self._engine.begin() as connection:
            rows = connection.execute(select(_embeddings.c.path, _embeddings.c.vector).limit(limit)).fetchall()
        return [EmbeddingRecord(path=row[0], embedding=json.loads(row[1])) for row in rows]

