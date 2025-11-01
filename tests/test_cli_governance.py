"""Tests for governance CLI."""

import json
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_governance_bundle_and_policy(tmp_path: Path) -> None:
    evaluation = tmp_path / "evaluation.json"
    evaluation.write_text(
        json.dumps(
            {
                "evaluation": {"suite": "lite", "metrics": {"bias_score": 0.01}, "sbom": "sbom.json"},
                "policy_overrides": [],
            }
        ),
        encoding="utf-8",
    )
    bundle_dest = tmp_path / "bundle.json"
    bundle = runner.invoke(
        app,
        ["governance", "bundle", "--evaluation", str(evaluation), "--output", str(bundle_dest)],
    )
    assert bundle.exit_code == 0
    assert bundle_dest.exists()
    payload = json.loads(bundle_dest.read_text(encoding="utf-8"))
    assert "ethics_charter" in payload

    policy = runner.invoke(app, ["governance", "policy", str(bundle_dest)])
    assert policy.exit_code == 0


def test_governance_compliance() -> None:
    result = runner.invoke(app, ["governance", "compliance"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["framework"].startswith("SOC2")
    assert "summary" in data
