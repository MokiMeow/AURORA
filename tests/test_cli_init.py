"""Tests for workspace initialization."""

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app


def test_init_creates_runtime_directories(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["init", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / "artifacts").is_dir()
    assert (tmp_path / "telemetry").is_dir()
    assert (tmp_path / "experience").is_dir()
