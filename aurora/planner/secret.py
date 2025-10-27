"""Secret redaction utilities for planner inputs/outputs."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class Redactor:
    patterns: tuple[re.Pattern, ...]
    replacement: str = "<REDACTED>"

    def redact(self, text: str) -> tuple[str, bool]:
        redacted = text
        hits = False
        for pattern in self.patterns:
            if pattern.search(redacted):
                hits = True
                redacted = pattern.sub(self.replacement, redacted)
        return redacted, hits


def build_redactor(patterns: tuple[str, ...], replacement: str = "<REDACTED>") -> Redactor:
    compiled = tuple(re.compile(pattern) for pattern in patterns)
    return Redactor(patterns=compiled, replacement=replacement)

