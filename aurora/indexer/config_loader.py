"""Load indexer configuration from YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import IndexerConfig, LanguageConfig, LanguageQueries


def load_indexer_config(base_path: Path, path: Path) -> IndexerConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    languages = _load_languages(base_path, data.get("languages_path", "configs/languages.yaml"))
    root = (base_path / data.get("root", ".")).resolve()
    return IndexerConfig(
        root=root,
        languages=languages,
        database_url=data["database_url"],
        embeddings_enabled=data.get("embeddings_enabled", True),
        embedding_model=data.get("embedding_model", "hash32"),
        milvus_enabled=data.get("milvus_enabled", False),
        milvus_uri=data.get("milvus_uri"),
        neo4j_uri=data.get("neo4j", {}).get("uri"),
        neo4j_user=data.get("neo4j", {}).get("user"),
        neo4j_password=data.get("neo4j", {}).get("password"),
        include_tests=data.get("include_tests", True),
        include_docs=data.get("include_docs", True),
        swe_telemetry_path=(Path(data["swe_telemetry_path"]).resolve() if data.get("swe_telemetry_path") else None),
        policy_notes=tuple(data.get("policy_notes", [])),
    )


def _load_languages(base_path: Path, config_path: str) -> tuple[LanguageConfig, ...]:
    languages_data = yaml.safe_load((base_path / config_path).read_text(encoding="utf-8"))
    languages = []
    for language in languages_data["languages"]:
        queries = None
        if "queries" in language:
            q = language["queries"]
            queries = LanguageQueries(
                symbols=(base_path / q["symbols"]).resolve() if q.get("symbols") else None,
                imports=(base_path / q["imports"]).resolve() if q.get("imports") else None,
                calls=(base_path / q["calls"]).resolve() if q.get("calls") else None,
            )
        languages.append(
            LanguageConfig(
                name=language["name"],
                tree_sitter=language["tree_sitter"],
                file_extensions=tuple(language["file_extensions"]),
                incremental=language.get("incremental", True),
                queries=queries,
            )
        )
    return tuple(languages)

