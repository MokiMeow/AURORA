"""Configuration models for the indexing subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class LanguageQueries:
    symbols: Path | None = None
    imports: Path | None = None
    calls: Path | None = None


@dataclass(slots=True)
class LanguageConfig:
    name: str
    tree_sitter: str
    file_extensions: tuple[str, ...]
    incremental: bool
    queries: LanguageQueries | None = None


@dataclass(slots=True)
class IndexerConfig:
    root: Path
    languages: tuple[LanguageConfig, ...]
    database_url: str
    embeddings_enabled: bool = True
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    milvus_enabled: bool = False
    milvus_uri: str | None = None
    neo4j_uri: str | None = None
    neo4j_user: str | None = None
    neo4j_password: str | None = None
    include_tests: bool = True
    include_docs: bool = True
    swe_telemetry_path: Path | None = None
    policy_notes: tuple[dict, ...] = ()

