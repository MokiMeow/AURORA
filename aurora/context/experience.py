"""Experience vault for storing and retrieving past self-edits."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ExperienceRecord:
    context: dict[str, Any]
    edit: dict[str, Any]
    telemetry: dict[str, Any]
    reward: float
    regret: bool


class ExperienceVault:
    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path or Path("experience/log.jsonl")
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: ExperienceRecord) -> None:
        with self._storage_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.__dict__) + "\n")

    def iter_records(self) -> list[ExperienceRecord]:
        records: list[ExperienceRecord] = []
        if not self._storage_path.exists():
            return records
        for line in self._storage_path.read_text(encoding="utf-8").splitlines():
            data = json.loads(line)
            records.append(ExperienceRecord(**data))
        return records

    def search(self, query: str, limit: int = 5) -> list[ExperienceRecord]:
        results: list[ExperienceRecord] = []
        for record in self.iter_records():
            content = json.dumps(record.context) + json.dumps(record.edit)
            if query.lower() in content.lower():
                results.append(record)
            if len(results) >= limit:
                break
        return results

    def iter_recent(self, limit: int = 20) -> list[ExperienceRecord]:
        records = self.iter_records()
        if not records:
            return []
        return list(reversed(records))[:limit]

