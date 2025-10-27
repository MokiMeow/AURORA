"""Secret scanning utilities."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import yaml

from aurora.telemetry.errors import ErrorLogger


@dataclass(slots=True)
class ExternalScannerConfig:
    name: str
    command: Sequence[str]
    timeout: int = 60
    allow_exit_codes: tuple[int, ...] = (0,)


@dataclass(slots=True)
class SecretScannerConfig:
    patterns: Iterable[str]
    replacement: str = "<REDACTED>"
    allow_patterns: Sequence[str] | None = None
    exclude_globs: Sequence[str] | None = None
    external: Sequence[ExternalScannerConfig] | None = None
    error_logger: ErrorLogger | None = None


class SecretScanner:
    def __init__(self, config: SecretScannerConfig) -> None:
        self._patterns = [re.compile(pattern) for pattern in config.patterns]
        self._allow_patterns = [re.compile(pattern) for pattern in (config.allow_patterns or [])]
        self._exclude_globs = tuple(config.exclude_globs or ())
        self._external = tuple(config.external or ())
        self._replacement = config.replacement
        self._errors = config.error_logger

    def scan_text(self, text: str) -> tuple[bool, str]:
        redacted = text
        found = False
        for pattern in self._patterns:
            if pattern.search(redacted):
                if self._is_allowed(pattern.pattern):
                    continue
                found = True
                redacted = pattern.sub(self._replacement, redacted)
        return found, redacted

    def scan_file(self, path: Path) -> tuple[bool, str]:
        if self._is_excluded(path):
            return False, path.read_text(encoding="utf-8")
        content = path.read_text(encoding="utf-8")
        found, redacted = self.scan_text(content)
        external_hits = self._run_external_scanners(path)
        return found or external_hits, redacted

    def _is_allowed(self, value: str) -> bool:
        return any(pattern.search(value) for pattern in self._allow_patterns)

    def _is_excluded(self, path: Path) -> bool:
        normalized = path.as_posix()
        for glob in self._exclude_globs:
            if path.match(glob) or normalized.endswith(glob.strip("*")):
                return True
        return False

    def _run_external_scanners(self, path: Path) -> bool:
        hit = False
        for scanner in self._external:
            command = [arg.format(path=str(path)) for arg in scanner.command]
            try:
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=scanner.timeout,
                )
            except Exception as exc:  # pragma: no cover - defensive
                if self._errors:
                    self._errors.log(
                        "secret_scanner_error",
                        f"{scanner.name} invocation failed",
                        {"path": str(path), "error": str(exc)},
                    )
                continue
            if result.returncode not in scanner.allow_exit_codes:
                self._log_secret(scanner.name, path, result)
                hit = True
            elif result.stdout.strip():
                self._log_secret(scanner.name, path, result)
                hit = True
        return hit

    def _log_secret(self, scanner: str, path: Path, result: subprocess.CompletedProcess[str]) -> None:
        if self._errors:
            self._errors.log(
                "secret_detection",
                f"{scanner} detected potential secret",
                {"path": str(path), "stdout": result.stdout, "stderr": result.stderr},
            )


def load_secret_scanner_config(path: Path, error_logger: ErrorLogger | None = None) -> SecretScannerConfig:
    if not path.exists():
        raise FileNotFoundError(f"Secret scanner configuration {path} not found")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    patterns = data.get("patterns", [])
    if not patterns:
        raise ValueError("Secret scanner configuration must define at least one pattern")
    external_cfgs = []
    for entry in data.get("external", []):
        external_cfgs.append(
            ExternalScannerConfig(
                name=entry["name"],
                command=entry["command"],
                timeout=entry.get("timeout", 60),
                allow_exit_codes=tuple(entry.get("allow_exit_codes", (0,))),
            )
        )
    return SecretScannerConfig(
        patterns=patterns,
        replacement=data.get("replacement", "<REDACTED>"),
        allow_patterns=data.get("allow_patterns"),
        exclude_globs=data.get("exclude_globs"),
        external=external_cfgs,
        error_logger=error_logger,
    )
