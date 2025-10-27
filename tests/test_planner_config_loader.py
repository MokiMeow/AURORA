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
swe_telemetry_path: telemetry/swe.json
policy_notes:
  - message: "Respect security policies"
    path: policies/security.yaml
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
experience:
  path: experience/log.jsonl
routes:
  - name: ollama_primary
    provider: ollama
    endpoint: http://localhost:11434/api/generate
    model: deepseek-r1:7b
    timeout_seconds: 60
  - name: openai_fallback
    provider: openai
    endpoint: https://api.openai.com/v1/chat/completions
    model: gpt-4o-mini
    timeout_seconds: 45
    keywords: ["cloud"]
routing:
  default_route: ollama_primary
  rules:
    - name: security-route
      route: openai_fallback
      keywords:
        - security
      auto_only: false
critic_strategy:
  mode: quorum
  threshold: 1
  priority:
    - critic-one
""",
        encoding="utf-8",
    )

    config = load_planner_config(config_yaml)

    assert config.primary.endpoint == "http://localhost:11434/api/generate"
    assert config.critics[0].name == "critic-one"
    assert config.retry_policy.max_attempts == 5
    assert config.secret_redaction.enabled is True
    assert config.experience_config is not None
    assert len(config.routes) >= 2
    assert config.routing is not None
    assert config.routing.default_route == "ollama_primary"
    assert config.critic_strategy.mode == "quorum"
    assert config.policy_notes and config.policy_notes[0]["message"] == "Respect security policies"

