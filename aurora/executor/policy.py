"""Policy evaluation for executor acceptance gates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class PolicyResult:
    accepted: bool
    reasons: list[str]


@dataclass(slots=True)
class PolicyMetadata:
    sbom: dict[str, Any] | None = None
    cve_report: dict[str, Any] | None = None
    license_report: dict[str, Any] | None = None
    artifacts_dir: str | None = None


class PolicyEvaluator:
    def __init__(self, policy_path: Path | None) -> None:
        self._policy_path = policy_path
        self._policy = self._load_policy()

    def evaluate(self, ci_results: list[dict], metadata: dict[str, Any] | PolicyMetadata | None = None) -> PolicyResult:
        reasons: list[str] = []
        accepted = True
        metadata_obj = self._to_metadata(metadata)

        ci_policy = (self._policy or {}).get("ci", {})
        required_steps = ci_policy.get("required_steps", [])
        allow_failures = set(ci_policy.get("allow_failures", []))
        for result in ci_results:
            if not result["success"] and result["step"] not in allow_failures:
                accepted = False
                reasons.append(f"CI step failed: {result['step']}")
        for rule in required_steps:
            if not any(rule == result["step"] and result["success"] for result in ci_results):
                accepted = False
                reasons.append(f"Required step missing: {rule}")

        if self._policy:
            self._evaluate_sbom(metadata_obj, reasons)
            self._evaluate_cve(metadata_obj, reasons)
            self._evaluate_licenses(metadata_obj, reasons)

        return PolicyResult(accepted=accepted and not reasons, reasons=reasons)

    def _evaluate_sbom(self, metadata: PolicyMetadata, reasons: list[str]) -> None:
        sbom_policy = self._policy.get("sbom", {}) if self._policy else {}
        if not sbom_policy.get("required"):
            return
        sbom = metadata.sbom
        if not isinstance(sbom, dict):
            reasons.append("SBOM artifact missing")
            return
        if sbom.get("warning") or sbom.get("error"):
            reasons.append("SBOM generation did not complete successfully")
            return
        components = sbom.get("components", sbom.get("packages"))
        if not isinstance(components, list) or not components:
            reasons.append("SBOM contains no package inventory")

    def _evaluate_cve(self, metadata: PolicyMetadata, reasons: list[str]) -> None:
        cve_policy = self._policy.get("cve", {}) if self._policy else {}
        if not cve_policy:
            return
        report = metadata.cve_report
        if report is None:
            reasons.append("CVE report missing")
            return
        if report.get("warning") or report.get("error"):
            reasons.append("CVE scan did not complete successfully")
            return
        summary = report.get("summary")
        if not isinstance(summary, dict):
            reasons.append("CVE report summary missing")
            return
        max_critical = cve_policy.get("max_critical", 0)
        max_high = cve_policy.get("max_high", 0)
        critical = summary.get("critical")
        high = summary.get("high")
        if not isinstance(critical, int) or not isinstance(high, int):
            reasons.append("CVE report summary is incomplete")
            return
        if critical > max_critical:
            reasons.append(f"Critical vulnerabilities exceed threshold ({critical} > {max_critical})")
        if high > max_high:
            reasons.append(f"High vulnerabilities exceed threshold ({high} > {max_high})")

    def _evaluate_licenses(self, metadata: PolicyMetadata, reasons: list[str]) -> None:
        license_policy = self._policy.get("licenses", {}) if self._policy else {}
        if not license_policy:
            return
        report = metadata.license_report
        if report is None:
            reasons.append("License report missing")
            return
        if report.get("warning") or report.get("error"):
            reasons.append("License scan did not complete successfully")
            return
        packages = report.get("packages")
        if not isinstance(packages, list) or not packages:
            reasons.append("License report contains no package inventory")
            return
        allowed = set(license_policy.get("allow", []))
        denied = set(license_policy.get("deny", []))
        for package in packages:
            license_id = package.get("license")
            name = package.get("name", "unknown")
            if license_id in denied:
                reasons.append(f"Denied license {license_id} detected in {name}")
            if allowed and license_id not in allowed:
                reasons.append(f"License {license_id} for {name} not in allow-list")

    def _to_metadata(self, metadata: dict[str, Any] | PolicyMetadata | None) -> PolicyMetadata:
        if metadata is None:
            return PolicyMetadata()
        if isinstance(metadata, PolicyMetadata):
            return metadata
        return PolicyMetadata(
            sbom=metadata.get("sbom"),
            cve_report=metadata.get("cve_report"),
            license_report=metadata.get("license_report"),
            artifacts_dir=metadata.get("artifacts_dir"),
        )

    def _load_policy(self) -> dict[str, Any] | None:
        if not self._policy_path:
            return None
        if not self._policy_path.exists():
            raise FileNotFoundError(f"Policy file not found: {self._policy_path}")
        text = self._policy_path.read_text(encoding="utf-8").strip()
        if not text:
            return {}
        suffix = self._policy_path.suffix.lower()
        if suffix in {".yaml", ".yml"}:
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
        return data or {}

