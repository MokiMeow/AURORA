"""Graph representation for repository symbols and relations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(slots=True)
class GraphNode:
    path: str
    symbols: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)


@dataclass(slots=True)
class GraphEdge:
    source: str
    target: str
    kind: str


class CodeGraph:
    def __init__(self) -> None:
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []

    def add_node(self, path: str, symbols: List[str], tests: List[str]) -> None:
        self.nodes[path] = GraphNode(path=path, symbols=symbols, tests=tests)

    def add_edge(self, source: str, target: str, kind: str) -> None:
        self.edges.append(GraphEdge(source=source, target=target, kind=kind))

    def neighbors(self, path: str, kind: str | None = None) -> List[str]:
        return [edge.target for edge in self.edges if edge.source == path and (kind is None or edge.kind == kind)]

