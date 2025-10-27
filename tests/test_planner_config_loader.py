"""Tests for planner configuration loader."""

from pathlib import Path

from aurora.planner.config_loader import load_planner_config


def test_load_planner_config(tmp_path: Path):
    config_yaml = tmp_path / "model.yaml"
    config_yaml.write_text(
        """
primary:
  provider: ollama
  endpoint: http://localhost:11434/api/generate
  model: deepseek-r1:7b
critic_stack:
  - name: critic-one
    endpoint: http://critic
    api_key_env: CRITIC_KEY
    enabled: true
retry_policy:
  max_attempts: 5
  backoff_seconds: 10
secret_redaction:
  enabled: true
  patterns:
    - secret
""",
        encoding="utf-8",
    )

    config = load_planner_config(config_yaml)

    assert config.primary.endpoint == "http://localhost:11434/api/generate"
    assert config.critics[0].name == "critic-one"
    assert config.retry_policy.max_attempts == 5
    assert config.secret_redaction.enabled is True

