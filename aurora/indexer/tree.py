"""Tree-sitter parsing utilities for AURORA-SE indexer."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from tree_sitter import Language, Parser
from tree_sitter_languages import get_parser, get_language

from .config import IndexerConfig, LanguageConfig

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SourceFile:
    path: Path
    language: LanguageConfig
    content: str


@dataclass(slots=True)
class ParsedUnit:
    path: Path
    language: str
    tree: object
    symbols: list[str]
    imports: list[str]
    content: str


class TreeSitterParser:
    def __init__(self, config: IndexerConfig) -> None:
        self._config = config
        self._parsers = {
            lang.name: self._build_parser(lang.tree_sitter)
            for lang in config.languages
        }

    def scan_repository(self, root: Path) -> Iterator[SourceFile]:
        for language in self._config.languages:
            for extension in language.file_extensions:
                for path in root.rglob(f"*{extension}"):
                    if path.is_file():
                        yield SourceFile(
                            path=path,
                            language=language,
                            content=path.read_text(encoding="utf-8"),
                        )

    def parse_sources(self, sources: Iterable[SourceFile]) -> Iterator[ParsedUnit]:
        for source in sources:
            parser = self._parsers.get(source.language.name)
            if not parser:
                LOGGER.warning("No parser for language %s", source.language.name)
                continue
            tree = parser.parse(source.content.encode("utf-8"))
            symbols, imports = self._run_queries(parser, tree, source)
            yield ParsedUnit(
                path=source.path,
                language=source.language.name,
                tree=tree,
                symbols=symbols,
                imports=imports,
                content=source.content,
            )

    def _run_queries(
        self,
        parser: Parser,
        tree: object,
        source: SourceFile,
    ) -> tuple[list[str], list[str]]:
        language_config = source.language
        symbols: list[str] = []
        imports: list[str] = []
        queries = language_config.queries
        if not queries:
            return symbols, imports
        if queries.symbols:
            symbols.extend(
                self._execute_query(
                    parser,
                    tree,
                    source,
                    queries.symbols,
                ),
            )
        if queries.imports:
            imports.extend(
                self._execute_query(
                    parser,
                    tree,
                    source,
                    queries.imports,
                ),
            )
        return symbols, imports

    @staticmethod
    def _execute_query(
        parser: Parser,
        tree: object,
        source: SourceFile,
        query_path: Path,
    ) -> list[str]:
        if not query_path.exists():
            return []
        query = parser.language.query(query_path.read_text(encoding="utf-8"))
        content_bytes = source.content.encode("utf-8")
        matches = query.captures(tree.root_node)
        results: list[str] = []
        for node, _ in matches:
            results.append(content_bytes[node.start_byte : node.end_byte].decode("utf-8"))
        return results

    @staticmethod
    def _build_parser(language_name: str) -> Parser:
        language = get_language(language_name)
        parser = Parser()
        parser.set_language(language)
        return parser

