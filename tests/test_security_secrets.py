"""Tests for enhanced secret scanner."""

from pathlib import Path

import subprocess

from aurora.security.secrets import ExternalScannerConfig, SecretScanner, SecretScannerConfig


class DummyCompletedProcess(subprocess.CompletedProcess):
    def __init__(self, args, returncode=0, stdout="", stderr=""):
        super().__init__(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


def test_secret_scanner_allow_pattern():
    config = SecretScannerConfig(patterns=(r"SAFE_TOKEN=\w+",), allow_patterns=("SAFE_TOKEN",))
    scanner = SecretScanner(config)
    found, _ = scanner.scan_text("SAFE_TOKEN=12345")
    assert found is False


def test_secret_scanner_external_detection(monkeypatch, tmp_path: Path):
    file_path = tmp_path / "suspect.txt"
    file_path.write_text("clean content", encoding="utf-8")

    def fake_run(command, check=False, capture_output=True, text=True, timeout=60):
        return DummyCompletedProcess(command, returncode=1, stdout="secret found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    config = SecretScannerConfig(
        patterns=(r"API_KEY",),
        external=(ExternalScannerConfig(name="fake", command=["scanner", "{path}"] ),),
    )
    scanner = SecretScanner(config)
    found, _ = scanner.scan_file(file_path)
    assert found is True
