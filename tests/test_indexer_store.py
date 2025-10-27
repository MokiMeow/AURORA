"""Tests for graph store persistence."""

from pathlib import Path

from aurora.indexer.store import GraphStore
from aurora.indexer.tree import ParsedUnit


def test_graph_store_persists_units(tmp_path: Path):
    store = GraphStore(database_url=f"sqlite:///{tmp_path / 'index.db'}")
    unit = ParsedUnit(
        path=tmp_path / "file.py",
        language="python",
        tree=None,
        symbols=["foo"],
        imports=["bar"],
        content="def foo(): pass",
        tests=[],
        calls=["bar"],
    )
    changed = store.store_units([unit], full=True)
    assert changed
    matches = store.find_symbols("foo", limit=5)
    assert matches

