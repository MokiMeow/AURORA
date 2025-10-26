"""Graph storage for repository intelligence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Iterator

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.sql import insert

from .tree import ParsedUnit

metadata = MetaData()

files_table = Table(
    "files",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("path", String, unique=True, nullable=False),
    Column("language", String, nullable=False),
    Column("ast", String, nullable=False),
    Column("symbols", String, nullable=False),
    Column("imports", String, nullable=False),
    Column("content_hash", String, nullable=False),
)

edges_table = Table(
    "edges",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("source", String, nullable=False),
    Column("target", String, nullable=False),
    Column("kind", String, nullable=False),
)

embeddings_table = Table(
    "embeddings",
    metadata,
    Column("path", String, primary_key=True),
    Column("vector", String, nullable=False),
)


@dataclass(slots=True)
class GraphStore:
    database_url: str

    def __post_init__(self) -> None:
        self._engine = create_engine(self.database_url, future=True)
        metadata.create_all(self._engine)

    def store_units(self, units: Iterable[ParsedUnit], full: bool) -> list[str]:
        changed_paths: list[str] = []
        with self._engine.begin() as connection:
            if full:
                connection.execute(delete(edges_table))
                connection.execute(delete(files_table))
            existing_hashes = self._load_hashes(connection) if not full else {}
            for unit in units:
                content_hash = hashlib.sha256(unit.content.encode("utf-8")).hexdigest()
                if not full and existing_hashes.get(str(unit.path)) == content_hash:
                    continue
                payload = {
                    "path": str(unit.path),
                    "language": unit.language,
                    "ast": json.dumps(unit.tree.root_node.sexp()),
                    "symbols": json.dumps(unit.symbols),
                    "imports": json.dumps(unit.imports),
                    "content_hash": content_hash,
                }
                connection.execute(
                    insert(files_table)
                    .values(payload)
                    .prefix_with("OR REPLACE")
                )
                connection.execute(delete(edges_table).where(edges_table.c.source == str(unit.path)))
                if unit.imports:
                    edge_payloads = [
                        {"source": str(unit.path), "target": target, "kind": "import"}
                        for target in unit.imports
                    ]
                    connection.execute(insert(edges_table), edge_payloads)
                changed_paths.append(str(unit.path))
        return changed_paths

    def find_symbols(self, term: str, limit: int = 10) -> list[str]:
        with self._engine.begin() as connection:
            rows = connection.execute(select(files_table.c.path, files_table.c.symbols)).fetchall()
        matches: list[str] = []
        for path, symbols_json in rows:
            symbols = json.loads(symbols_json)
            if any(term in symbol for symbol in symbols):
                matches.append(path)
                if len(matches) >= limit:
                    break
        return matches

    def neighbors(self, path: str, limit: int = 10) -> list[str]:
        with self._engine.begin() as connection:
            rows = connection.execute(
                select(edges_table.c.target)
                .where(edges_table.c.source == path)
                .limit(limit)
            ).fetchall()
        return [row[0] for row in rows]

    def list_files(self) -> Iterator[dict]:
        with self._engine.begin() as connection:
            result = connection.execute(select(files_table)).mappings()
            for row in result:
                yield dict(row)

    @property
    def engine(self) -> Engine:
        return self._engine

    @staticmethod
    def _load_hashes(connection) -> dict[str, str]:
        rows = connection.execute(select(files_table.c.path, files_table.c.content_hash)).fetchall()
        return {path: content_hash for path, content_hash in rows}

