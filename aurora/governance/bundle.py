"""Governance bundle assembly utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .automation import assemble_artifacts, save_bundle


@dataclass(slots=True)
class GovernanceBundle:
    output_path: Path
    payload: dict[str, Any]


def assemble_bundle(
    output_path: Path,
    evaluation_report: dict[str, Any],
    overrides: list[dict] | None = None,
    sbom_path: Path | None = None,
    cve_path: Path | None = None,
    alert_rules_path: Path | None = None,
) -> GovernanceBundle:
    bundle_dir = output_path.parent
    bundle_dir.mkdir(parents=True, exist_ok=True)
    artifacts = assemble_artifacts(
        evaluation_report=evaluation_report,
        overrides=overrides or [],
        sbom_path=sbom_path,
        cve_path=cve_path,
        alert_rules_path=alert_rules_path,
    )
    payload = save_bundle(output_path, artifacts)
    return GovernanceBundle(output_path=output_path, payload=payload)
