"""Tests for extension manager."""

from pathlib import Path

from aurora.extensions.manager import ExtensionManager


def test_extension_manager_loads(monkeypatch, tmp_path: Path) -> None:
    plugin_file = tmp_path / "demo_plugin.py"
    plugin_file.write_text(
        "from aurora.extensions.base import AuroraExtension\n\nclass Demo(AuroraExtension):\n    def on_autopilot_start(self):\n        self.started = True\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    manager = ExtensionManager()
    manager.load_many(["demo_plugin:Demo"])
    assert len(manager.extensions) == 1
    plugin = manager.extensions[0]
    plugin.on_autopilot_start()
    assert getattr(plugin, "started", False)


def test_extension_manager_from_config(monkeypatch, tmp_path: Path) -> None:
    plugin_file = tmp_path / "demo_plugin_cfg.py"
    plugin_file.write_text(
        "from aurora.extensions.base import AuroraExtension\n\nclass DemoCfg(AuroraExtension):\n    pass\n",
        encoding="utf-8",
    )
    config_file = tmp_path / "extensions.txt"
    config_file.write_text("demo_plugin_cfg:DemoCfg\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    manager = ExtensionManager.from_config(config_file)
    assert len(manager.extensions) == 1
