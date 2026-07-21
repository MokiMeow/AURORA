"""Tests for tree-sitter parser functionality."""

from pathlib import Path

import pytest

from aurora.indexer.config import IndexerConfig, LanguageConfig
from aurora.indexer.tree import TreeSitterParser


def make_config(tmp_path: Path) -> IndexerConfig:
    language = LanguageConfig(
        name="python",
        tree_sitter="python",
        file_extensions=(".py",),
        incremental=True,
        queries=None,
    )
    return IndexerConfig(
        root=tmp_path,
        languages=(language,),
        database_url="sqlite:///test.db",
    )


def test_parser_scans_python_files(tmp_path: Path):
    config = make_config(tmp_path)
    parser = TreeSitterParser(config)

    file_path = tmp_path / "example.py"
    file_path.write_text("def foo():\n    return 1\n", encoding="utf-8")

    sources = list(parser.scan_repository(tmp_path))
    assert len(sources) == 1
    assert sources[0].path == file_path

    units = list(parser.parse_sources(sources))
    assert len(units) == 1
    assert units[0].language == "python"
    assert units[0].symbols


def test_parser_skips_symlinked_source_files(tmp_path: Path):
    repository = tmp_path / "repository"
    repository.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("outside = True\n", encoding="utf-8")
    linked = repository / "linked.py"
    try:
        linked.symlink_to(outside)
    except OSError:
        pytest.skip("File symlinks are unavailable on this system")

    parser = TreeSitterParser(make_config(repository))

    assert list(parser.scan_repository(repository)) == []

