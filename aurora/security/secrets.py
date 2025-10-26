"""Secret scanning utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class SecretScannerConfig:
    patterns: Iterable[str]
    replacement: str = "<REDACTED>"


class SecretScanner:
    def __init__(self, config: SecretScannerConfig) -> None:
        self._patterns = [re.compile(pattern) for pattern in config.patterns]
        self._replacement = config.replacement

    def scan_text(self, text: str) -> tuple[bool, str]:
        redacted = text
        found = False
        for pattern in self._patterns:
            if pattern.search(redacted):
                found = True
                redacted = pattern.sub(self._replacement, redacted)
        return found, redacted

    def scan_file(self, path: Path) -> tuple[bool, str]:
        content = path.read_text(encoding="utf-8")
        return self.scan_text(content)

