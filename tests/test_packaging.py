"""Regression tests for distributable package behavior."""

from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_TREES = ("configs", "policies", "prompts", "queries", "scripts")


def test_wheel_contains_runtime_resources_and_license(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "wheel"
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--wheel-dir", str(wheel_dir)],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel_path = next(wheel_dir.glob("*.whl"))

    with zipfile.ZipFile(wheel_path) as archive:
        names = archive.namelist()

    for tree_name in RESOURCE_TREES:
        prefix = f"aurora/resources/{tree_name}/"
        assert any(name.startswith(prefix) for name in names)
    assert any(name.endswith(".dist-info/licenses/LICENSE") for name in names)
    assert not any("/__pycache__/" in name or name.endswith((".pyc", ".pyo")) for name in names)


def test_cli_import_and_help_do_not_mutate_empty_working_directory(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(PROJECT_ROOT), environment.get("PYTHONPATH")))
    )
    import_directory = tmp_path / "import"
    help_directory = tmp_path / "help"
    import_directory.mkdir()
    help_directory.mkdir()

    subprocess.run(
        [sys.executable, "-c", "import cli.main"],
        cwd=import_directory,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [sys.executable, "-m", "cli.main", "--help"],
        cwd=help_directory,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert list(import_directory.iterdir()) == []
    assert list(help_directory.iterdir()) == []
