"""Compliance automation utilities for SOC2/ISO style checklists."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import yaml


@dataclass(slots=True)
class ChecklistItem:
    id: str
    description: str
    status: str
    owner: str


@dataclass(slots=True)
class ComplianceChecklist:
    framework: str
    items: List[ChecklistItem]

    def as_dict(self) -> Dict[str, object]:
        return {
            "framework": self.framework,
            "items": [
                {"id": item.id, "description": item.description, "status": item.status, "owner": item.owner}
                for item in self.items
            ],
        }


def load_checklist(path: Path) -> ComplianceChecklist:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    framework = data.get("framework", "SOC2")
    items = [
        ChecklistItem(
            id=str(entry.get("id")),
            description=str(entry.get("description")),
            status=str(entry.get("status", "pending")),
            owner=str(entry.get("owner", "unassigned")),
        )
        for entry in data.get("items", [])
    ]
    return ComplianceChecklist(framework=framework, items=items)


def checklist_summary(checklist: ComplianceChecklist) -> Dict[str, int]:
    totals: Dict[str, int] = {}
    for item in checklist.items:
        totals[item.status] = totals.get(item.status, 0) + 1
    return totals
