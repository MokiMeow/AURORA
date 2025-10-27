"""Compliance policy engine for governance bundles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CompliancePolicy:
    max_bias_score: float
    require_sbom: bool = True

    def evaluate(self, report: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        bias = report.get("metrics", {}).get("bias_score")
        if bias and bias > self.max_bias_score:
            issues.append(f"Bias score {bias} exceeds {self.max_bias_score}")
        if self.require_sbom and not report.get("sbom"):
            issues.append("Missing SBOM reference")
        return issues

