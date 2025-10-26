"""Tests for loading indexer configuration."""

from pathlib import Path

from aurora.indexer.config_loader import load_indexer_config


def test_load_indexer_config(tmp_path: Path):
    config_yaml = tmp_path / "indexer.yaml"
    config_yaml.write_text(
        """database_url: sqlite:///test.db
root: .
languages_path: languages.yaml
""",
        encoding="utf-8",
    )
    languages_yaml = tmp_path / "languages.yaml"
    languages_yaml.write_text(
        """languages:
  - name: python
    tree_sitter: python
    file_extensions: [".py"]
    incremental: true
""",
        encoding="utf-8",
    )

    config = load_indexer_config(tmp_path, config_yaml)

    assert config.database_url == "sqlite:///test.db"
    assert config.root == tmp_path.resolve()
    assert len(config.languages) == 1
    assert config.languages[0].name == "python"

