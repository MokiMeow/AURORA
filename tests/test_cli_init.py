"""Tests for workspace initialization."""

import re
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app


def test_init_creates_runtime_directories(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["init", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / "artifacts").is_dir()
    assert (tmp_path / "telemetry").is_dir()
    assert (tmp_path / "experience").is_dir()
    assert (tmp_path / "configs" / "model.yaml").is_file()
    assert (tmp_path / "policies" / "security.yaml").is_file()
    assert (tmp_path / "prompts" / "planner_v1.md").is_file()
    assert (tmp_path / "queries" / "python.scm").is_file()
    assert (tmp_path / "scripts" / "eval_smoke.py").is_file()
    assert re.search(r"Created [1-9]\d* default files; skipped 0 existing files", result.output)


def test_init_is_idempotent_and_preserves_user_changes(tmp_path: Path) -> None:
    runner = CliRunner()
    first_result = runner.invoke(app, ["init", "--root", str(tmp_path)])
    config_path = tmp_path / "configs" / "model.yaml"
    config_path.write_text("user: customized\n", encoding="utf-8")

    second_result = runner.invoke(app, ["init", "--root", str(tmp_path)])

    assert first_result.exit_code == 0
    assert second_result.exit_code == 0
    assert config_path.read_text(encoding="utf-8") == "user: customized\n"
    created_match = re.search(r"Created (\d+) default files", first_result.output)
    skipped_match = re.search(r"skipped (\d+) existing files", second_result.output)
    assert created_match is not None
    assert skipped_match is not None
    assert int(created_match.group(1)) == int(skipped_match.group(1))
    assert "Created 0 default files" in second_result.output
