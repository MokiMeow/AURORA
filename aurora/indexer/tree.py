"""Tree-sitter parsing utilities for AURORA-SE indexer."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from tree_sitter import Parser
from tree_sitter_languages import get_language

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
    tests: list[str]
    calls: list[str]


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
            symbols, imports, calls = self._run_queries(parser, tree, source)
            if not symbols:
                symbols = [source.path.stem]
            tests = self._detect_tests(source)
            yield ParsedUnit(
                path=source.path,
                language=source.language.name,
                tree=tree,
                symbols=symbols,
                imports=imports,
                content=source.content,
                tests=tests,
                calls=calls,
            )

    def _run_queries(
        self,
        parser: Parser,
        tree: object,
        source: SourceFile,
    ) -> tuple[list[str], list[str], list[str]]:
        language_config = source.language
        symbols: list[str] = []
        imports: list[str] = []
        calls: list[str] = []
        queries = language_config.queries
        if not queries:
            return symbols, imports, calls
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
        if queries.calls:
            calls.extend(
                self._execute_query(
                    parser,
                    tree,
                    source,
                    queries.calls,
                ),
            )
        return symbols, imports, calls

    @staticmethod
    def _execute_query(
        parser: Parser,
        tree: object,
        source: SourceFile,
        query_path: Path,
    ) -> list[str]:
        if not query_path.exists():
            return []
        parser_language = getattr(parser, "language", None)
        if parser_language is None:
            raise AttributeError("Parser missing language configuration")
        query = parser_language.query(query_path.read_text(encoding="utf-8"))  # type: ignore[call-arg]
        content_bytes = source.content.encode("utf-8")
        root_node = getattr(tree, "root_node", None)
        if root_node is None:
            return []
        matches = query.captures(root_node)
        results: list[str] = []
        for node, _ in matches:
            results.append(content_bytes[node.start_byte : node.end_byte].decode("utf-8"))
        return results

    def _detect_tests(self, source: SourceFile) -> list[str]:
        if source.path.name.startswith("test_") or "/tests/" in str(source.path).replace("\\", "/"):
            return [source.path.as_posix()]
        return []

    @staticmethod
    def _build_parser(language_name: str) -> Parser:
        language = get_language(language_name)
        parser = Parser()
        parser.set_language(language)
        return parser

