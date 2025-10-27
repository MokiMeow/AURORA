"""Governance bundle assembly utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class GovernanceBundle:
    output_path: Path
    payload: dict[str, Any]


def assemble_bundle(output_path: Path, evaluation_report: dict[str, Any]) -> GovernanceBundle:
    bundle_dir = output_path.parent
    bundle_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "evaluation": evaluation_report,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return GovernanceBundle(output_path=output_path, payload=payload)

