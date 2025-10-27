"""Context packer for combining graph, embeddings, and experience signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from .store import GraphStore
from .embedding import EmbeddingStore
from .graph import CodeGraph


@dataclass(slots=True)
class ContextSlice:
    path: str
    summary: str
    score: float


class ExperienceVault(Protocol):
    def iter_recent(self, limit: int = 20) -> Iterable[dict]:
        ...


class ContextPacker:
    def __init__(
        self,
        graph_store: GraphStore,
        embedding_store: EmbeddingStore,
        experience_vault: ExperienceVault | None = None,
        limit: int = 20,
    ) -> None:
        self._graph_store = graph_store
        self._embedding_store = embedding_store
        self._experience_vault = experience_vault
        self._limit = limit

    def build_context(self, query: str) -> list[ContextSlice]:
        slices: list[ContextSlice] = []

        for path in self._graph_store.find_symbols(query, limit=self._limit):
            slices.append(ContextSlice(path=path, summary=f"Symbol match for {query}", score=0.9))
            for neighbor in self._graph_store.neighbors(path, kind="call"):
                slices.append(ContextSlice(path=neighbor, summary=f"Call neighbor of {path}", score=0.6))
            for neighbor in self._graph_store.neighbors(path, kind="import"):
                slices.append(ContextSlice(path=neighbor, summary=f"Import neighbor of {path}", score=0.5))

        for record in self._embedding_store.query(limit=self._limit):
            slices.append(
                ContextSlice(
                    path=record.path,
                    summary="Embedding candidate",
                    score=0.7,
                )
            )

        if self._experience_vault:
            for entry in self._experience_vault.iter_recent(limit=self._limit):
                slices.append(
                    ContextSlice(
                        path=entry.get("path", ""),
                        summary=entry.get("summary", "Experience vault record"),
                        score=entry.get("score", 0.5),
                    )
                )

        slices = sorted(slices, key=lambda s: s.score, reverse=True)
        deduped: list[ContextSlice] = []
        seen = set()
        for slice_ in slices:
            if slice_.path in seen or not slice_.path:
                continue
            deduped.append(slice_)
            seen.add(slice_.path)
            if len(deduped) >= self._limit:
                break
        return deduped

