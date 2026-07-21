"""Governance automation helpers for compliance bundles and reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List


@dataclass(slots=True)
class GovernanceArtifacts:
    evaluation: dict[str, Any]
    policy_overrides: List[dict[str, Any]]
    ethics_charter: str
    slo_summary: str
    alert_rules: str | None
    sbom_status: str | None
    cve_status: str | None
    swe_bench_trends: dict[str, Any]


def _safe_read(path: Path | None) -> str | None:
    if not path or not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


def load_ethics_charter(path: Path = Path("docs/governance/ethics_charter.md")) -> str:
    if not path.exists():
        return "Ethics charter document not found."
    return path.read_text(encoding="utf-8").strip()


def load_slo_summary(path: Path = Path("docs/operations/SLOs.md")) -> str:
    if not path.exists():
        return "SLO documentation not available."
    return path.read_text(encoding="utf-8").strip()


def load_alert_rules(path: Path | None) -> str | None:
    if path and path.exists():
        return path.read_text(encoding="utf-8").strip()
    return None


def load_swe_bench_trends(path: Path = Path("docs/reports/weekly_governance.md")) -> dict[str, Any]:
    if not path.exists():
        return {"status": "report_missing"}
    lines = path.read_text(encoding="utf-8").splitlines()
    highlights = [line for line in lines if line.startswith("- ")]
    return {"highlights": highlights, "source": str(path)}


def assemble_artifacts(
    evaluation_report: dict[str, Any],
    overrides: Iterable[dict[str, Any]] | None = None,
    sbom_path: Path | None = None,
    cve_path: Path | None = None,
    alert_rules_path: Path | None = None,
) -> GovernanceArtifacts:
    sbom_status = _safe_read(sbom_path)
    cve_status = _safe_read(cve_path)
    return GovernanceArtifacts(
        evaluation=evaluation_report,
        policy_overrides=list(overrides or []),
        ethics_charter=load_ethics_charter(),
        slo_summary=load_slo_summary(),
        alert_rules=load_alert_rules(alert_rules_path),
        sbom_status=sbom_status,
        cve_status=cve_status,
        swe_bench_trends=load_swe_bench_trends(),
    )


def render_bundle_payload(artifacts: GovernanceArtifacts) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "evaluation": artifacts.evaluation,
        "policy_overrides": artifacts.policy_overrides,
        "ethics_charter": artifacts.ethics_charter,
        "slo_summary": artifacts.slo_summary,
        "swe_bench_trends": artifacts.swe_bench_trends,
    }
    if artifacts.alert_rules:
        payload["alert_rules"] = artifacts.alert_rules
    if artifacts.sbom_status:
        payload["sbom_status"] = artifacts.sbom_status
    if artifacts.cve_status:
        payload["cve_status"] = artifacts.cve_status
    return payload


def save_bundle(
    output_path: Path,
    artifacts: GovernanceArtifacts,
) -> dict[str, Any]:
    payload = render_bundle_payload(artifacts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
