"""Tests for scripts CLI."""

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_scripts_run_python(tmp_path: Path) -> None:
    script = tmp_path / "demo.py"
    script.write_text("import sys\nprint('ok')\nsys.exit(0)\n", encoding="utf-8")
    result = runner.invoke(app, ["scripts", "run", str(script)])
    assert result.exit_code == 0
    assert "Script exited with code 0" in result.stdout
