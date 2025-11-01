"""Tests for plugin CLI."""

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_plugin_list(monkeypatch, tmp_path: Path) -> None:
    plugin_file = tmp_path / "demo_ext.py"
    plugin_file.write_text(
        "from aurora.extensions.base import AuroraExtension\n\nclass Demo(AuroraExtension):\n    def on_autopilot_start(self):\n        pass\n",
        encoding="utf-8",
    )
    config_file = tmp_path / "extensions.txt"
    config_file.write_text("demo_ext:Demo\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    result = runner.invoke(app, ["plugin", "list", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "Demo" in result.stdout


def test_plugin_install_and_remove(monkeypatch, tmp_path: Path) -> None:
    plugin_file = tmp_path / "demo_ext.py"
    plugin_file.write_text(
        "from aurora.extensions.base import AuroraExtension\n\nclass Demo(AuroraExtension):\n    def on_autopilot_start(self):\n        pass\n",
        encoding="utf-8",
    )
    config_file = tmp_path / "extensions.txt"
    monkeypatch.syspath_prepend(str(tmp_path))

    install = runner.invoke(
        app,
        [
            "plugin",
            "install",
            "demo",
            "--spec",
            "demo_ext:Demo",
            "--source",
            str(tmp_path),
            "--config",
            str(config_file),
        ],
    )
    assert install.exit_code == 0
    assert "Installed plugin" in install.stdout

    remove = runner.invoke(app, ["plugin", "remove", "demo", "--config", str(config_file)])
    assert remove.exit_code == 0
    assert "Removed plugin" in remove.stdout
