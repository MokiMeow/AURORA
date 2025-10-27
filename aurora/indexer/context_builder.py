"""Factory for building context packers with optional strategies."""

from __future__ import annotations

from .context import ContextPacker
from .store import GraphStore
from .embedding import EmbeddingStore


def build_context_packer(
    graph_store: GraphStore,
    embedding_store: EmbeddingStore,
    experience_vault=None,
    limit: int = 20,
    swe_telemetry_path=None,
    policy_notes=(),
) -> ContextPacker:
    return ContextPacker(
        graph_store=graph_store,
        embedding_store=embedding_store,
        experience_vault=experience_vault,
        limit=limit,
        swe_telemetry_path=swe_telemetry_path,
        policy_notes=policy_notes,
    )

