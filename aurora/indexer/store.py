"""Graph storage for repository intelligence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Iterable, Iterator

from neo4j import GraphDatabase

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.sql import insert

from .tree import ParsedUnit
from .graph import CodeGraph
from .config import IndexerConfig

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
    neo4j_url: str | None = None
    neo4j_user: str | None = None
    neo4j_password: str | None = None
    _neo4j_driver: GraphDatabase | None = field(init=False, default=None)
    _engine: Engine | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self._setup()

    def _setup(self) -> None:
        self._engine = create_engine(self.database_url, future=True)
        metadata.create_all(self._engine)
        if self.neo4j_url and self.neo4j_user and self.neo4j_password:
            self._neo4j_driver = GraphDatabase.driver(
                self.neo4j_url,
                auth=(self.neo4j_user, self.neo4j_password),
            )

    def store_units(self, units: Iterable[ParsedUnit], full: bool) -> list[str]:
        changed_paths: list[str] = []
        graph = CodeGraph()
        for unit in units:
            graph.add_node(str(unit.path), unit.symbols, unit.tests)
            for target in unit.imports:
                graph.add_edge(str(unit.path), target, "import")
            for call in unit.calls:
                graph.add_edge(str(unit.path), call, "call")
        with self._engine.begin() as connection:
            if full:
                connection.execute(delete(edges_table))
                connection.execute(delete(files_table))
            existing_hashes = self._load_hashes(connection) if not full else {}
            for path, node in graph.nodes.items():
                content_hash = hashlib.sha256((path + json.dumps(node.symbols)).encode("utf-8")).hexdigest()
                if not full and existing_hashes.get(path) == content_hash:
                    continue
                payload = {
                    "path": path,
                    "language": "unknown",
                    "ast": "{}",
                    "symbols": json.dumps(node.symbols),
                    "imports": "[]",
                    "content_hash": content_hash,
                }
                connection.execute(
                    insert(files_table)
                    .values(payload)
                    .prefix_with("OR REPLACE")
                )
                connection.execute(delete(edges_table).where(edges_table.c.source == path))
                edge_payloads = [
                    {"source": edge.source, "target": edge.target, "kind": edge.kind}
                    for edge in graph.edges
                    if edge.source == path
                ]
                if edge_payloads:
                    connection.execute(insert(edges_table), edge_payloads)
                changed_paths.append(path)
        if self._neo4j_driver:
            self._persist_neo4j(graph, full)
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

    def _persist_neo4j(self, graph: CodeGraph, full: bool) -> None:
        if not self._neo4j_driver:
            return
        with self._neo4j_driver.session() as session:
            if full:
                session.run("MATCH (n) DETACH DELETE n")
            for node in graph.nodes.values():
                session.run(
                    "MERGE (f:File {path: $path}) SET f.symbols = $symbols, f.tests = $tests",
                    path=node.path,
                    symbols=node.symbols,
                    tests=node.tests,
                )
            for edge in graph.edges:
                session.run(
                    "MATCH (a:File {path: $source}), (b:File {path: $target}) "
                    "MERGE (a)-[r:%s]->(b)"
                    % edge.kind.upper(),
                    source=edge.source,
                    target=edge.target,
                )

