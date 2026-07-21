"""Tests for policy CLI."""

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_policy_list_set_check(tmp_path: Path) -> None:
    config = Path("configs/policy_profiles.yaml")
    assert config.exists()
    active_path = tmp_path / "active.txt"
    list_result = runner.invoke(app, ["policy", "list", "--config", str(config)])
    assert list_result.exit_code == 0
    set_result = runner.invoke(
        app,
        ["policy", "set", "baseline", "--config", str(config), "--active-path", str(active_path)],
    )
    assert set_result.exit_code == 0
    policy = Path("policies/security.yaml")
    policy_data = yaml.safe_load(policy.read_text(encoding="utf-8"))
    results_path = tmp_path / "results.json"
    results_path.write_text(
        json.dumps(
            [
                {"step": step, "success": True}
                for step in policy_data["ci"]["required_steps"]
            ]
        ),
        encoding="utf-8",
    )
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "sbom": {"components": [{"name": "aurora-se"}]},
                "cve_report": {"summary": {"critical": 0, "high": 0}},
                "license_report": {"packages": [{"name": "aurora-se", "license": "Apache-2.0"}]},
            }
        ),
        encoding="utf-8",
    )
    check_result = runner.invoke(
        app,
        [
            "policy",
            "check",
            "--profile",
            "baseline",
            "--config",
            str(config),
            "--results",
            str(results_path),
            "--metadata",
            str(metadata_path),
        ],
    )
    assert check_result.exit_code == 0
    assert '"accepted": true' in check_result.stdout
