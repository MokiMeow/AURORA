"""Tests for executor policy evaluator."""

from pathlib import Path

import yaml

from aurora.executor.policy import PolicyEvaluator, PolicyMetadata


def _write_policy(tmp_path: Path, data: dict) -> Path:
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text(yaml.safe_dump(data))
    return policy_file


def test_policy_accepts_success(tmp_path: Path):
    policy_path = _write_policy(
        tmp_path,
        {
            "ci": {"required_steps": ["lint"]},
            "sbom": {"required": False},
            "cve": {},
            "licenses": {},
        },
    )
    evaluator = PolicyEvaluator(policy_path=policy_path)
    result = evaluator.evaluate([
        {"step": "lint", "success": True, "log": "lint.log"},
    ])
    assert result.accepted is True


def test_policy_rejects_missing_step(tmp_path: Path):
    policy_path = _write_policy(
        tmp_path,
        {
            "ci": {"required_steps": ["lint", "sbom_generate"]},
            "sbom": {"required": True},
            "cve": {},
            "licenses": {},
        },
    )
    evaluator = PolicyEvaluator(policy_path=policy_path)
    metadata = PolicyMetadata(sbom={"packages": []})
    result = evaluator.evaluate([
        {"step": "lint", "success": True, "log": "lint.log"},
    ], metadata=metadata)
    assert result.accepted is False
    assert any("Required step" in reason for reason in result.reasons)


def test_policy_enforces_sbom(tmp_path: Path):
    policy_path = _write_policy(
        tmp_path,
        {
            "ci": {"required_steps": []},
            "sbom": {"required": True},
            "cve": {},
            "licenses": {},
        },
    )
    evaluator = PolicyEvaluator(policy_path=policy_path)
    result = evaluator.evaluate([], metadata=PolicyMetadata())
    assert result.accepted is False
    assert any("SBOM" in reason for reason in result.reasons)


def test_policy_enforces_cve_threshold(tmp_path: Path):
    policy_path = _write_policy(
        tmp_path,
        {
            "ci": {"required_steps": []},
            "sbom": {"required": False},
            "cve": {"max_critical": 0, "max_high": 1},
            "licenses": {},
        },
    )
    evaluator = PolicyEvaluator(policy_path=policy_path)
    metadata = PolicyMetadata(cve_report={"summary": {"critical": 1, "high": 0}})
    result = evaluator.evaluate([], metadata=metadata)
    assert result.accepted is False
    assert any("Critical vulnerabilities" in reason for reason in result.reasons)


def test_policy_enforces_license_allowlist(tmp_path: Path):
    policy_path = _write_policy(
        tmp_path,
        {
            "ci": {"required_steps": []},
            "sbom": {"required": False},
            "cve": {},
            "licenses": {"allow": ["Apache-2.0"], "deny": ["GPL-3.0"]},
        },
    )
    evaluator = PolicyEvaluator(policy_path=policy_path)
    metadata = PolicyMetadata(
        license_report={
            "packages": [
                {"name": "aurora", "license": "Apache-2.0"},
                {"name": "forbidden", "license": "GPL-3.0"},
            ]
        }
    )
    result = evaluator.evaluate([], metadata=metadata)
    assert result.accepted is False
    assert any("Denied license" in reason for reason in result.reasons)


def test_policy_requires_exact_step_names(tmp_path: Path) -> None:
    policy_path = _write_policy(tmp_path, {"ci": {"required_steps": ["lint"]}})
    result = PolicyEvaluator(policy_path).evaluate([{"step": "not-linting", "success": True}])
    assert result.accepted is False


def test_policy_rejects_placeholder_evidence(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path,
        {
            "ci": {"required_steps": []},
            "sbom": {"required": True},
            "cve": {"max_critical": 0, "max_high": 0},
            "licenses": {"allow": ["MIT"]},
        },
    )
    metadata = PolicyMetadata(
        sbom={"warning": "scanner missing"},
        cve_report={"warning": "scanner missing"},
        license_report={"warning": "scanner missing", "packages": []},
    )
    result = PolicyEvaluator(policy_path).evaluate([], metadata)
    assert result.accepted is False
    assert len(result.reasons) == 3
