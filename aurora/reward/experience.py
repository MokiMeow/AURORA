"""Experience vault logging for reward outcomes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable


@dataclass(slots=True)
class ExperienceRecord:
    context: dict[str, Any]
    edit: dict[str, Any]
    telemetry: dict[str, Any]
    reward: float
    regret: bool
    metadata: dict[str, Any] | None = None


class ExperienceLogger:
    def __init__(
        self,
        log_path: Path,
        index_root: Path | None = None,
        max_records: int = 5000,
        retention_days: int = 180,
        dedupe_fields: Iterable[str] | None = None,
        redact_fields: Iterable[str] | None = None,
        compress: bool = False,
    ) -> None:
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._index_root = index_root or (self._log_path.parent / "indices")
        self._index_root.mkdir(parents=True, exist_ok=True)
        self._max_records = max_records
        self._retention_days = retention_days
        self._dedupe_fields = tuple(dedupe_fields or ())
        self._redact_fields = tuple(redact_fields or ())
        self._compress = compress

        self._dedupe_cache: set[str] = set()
        self._dedupe_store = self._index_root / "dedupe.json"
        self._task_index = self._index_root / "task_index.json"
        self._reward_index = self._index_root / "top_rewards.json"
        self._policy_index = self._index_root / "policy_index.json"
        self._load_state()

    def append(self, record: ExperienceRecord) -> None:
        entry = self._prepare_entry(record)
        dedupe_key = self._fingerprint(entry)
        if self._dedupe_fields and dedupe_key in self._dedupe_cache:
            return

        self._append_entry(entry)
        self._update_indexes(entry)
        if self._dedupe_fields:
            self._dedupe_cache.add(dedupe_key)
            self._persist_dedupe()
        self._enforce_limits()

    def log_regret(self, context: dict, telemetry: dict, reward: float) -> None:
        self.append(
            ExperienceRecord(
                context=context,
                edit={"summary": "regret"},
                telemetry=telemetry,
                reward=reward,
                regret=True,
            )
        )

    def _prepare_entry(self, record: ExperienceRecord) -> dict[str, Any]:
        timestamp = datetime.utcnow().isoformat()
        context = self._redact_mapping(record.context)
        edit = self._redact_mapping(record.edit)
        telemetry = self._redact_mapping(record.telemetry)
        entry = {
            "timestamp": timestamp,
            "context": context,
            "edit": edit,
            "telemetry": telemetry,
            "reward": record.reward,
            "regret": record.regret,
            "metadata": record.metadata or {},
        }
        return entry

    def _append_entry(self, entry: dict[str, Any]) -> None:
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def _update_indexes(self, entry: dict[str, Any]) -> None:
        task_id = (
            entry["context"].get("task_id")
            or entry["context"].get("task")
            or entry["metadata"].get("task_id")
        )
        if task_id:
            task_index = self._load_index(self._task_index)
            task_entries = task_index.get(task_id, [])
            task_entries.append({"timestamp": entry["timestamp"], "reward": entry["reward"]})
            task_index[task_id] = task_entries[-20:]
            self._write_index(self._task_index, task_index)

        reward_index = self._load_index(self._reward_index, default=[])
        reward_index.append(
            {
                "timestamp": entry["timestamp"],
                "reward": entry["reward"],
                "regret": entry["regret"],
                "task": task_id,
            }
        )
        reward_index = sorted(reward_index, key=lambda e: e["reward"], reverse=True)[:50]
        self._write_index(self._reward_index, reward_index)

        policy_notes = entry["telemetry"].get("policy") or entry["metadata"].get("policy_reasons") or []
        if policy_notes:
            policy_index = self._load_index(self._policy_index)
            for note in policy_notes:
                bucket = policy_index.get(note, [])
                bucket.append({"timestamp": entry["timestamp"], "reward": entry["reward"]})
                policy_index[note] = bucket[-20:]
            self._write_index(self._policy_index, policy_index)

    def _enforce_limits(self) -> None:
        entries = self._load_entries()
        cutoff = datetime.utcnow() - timedelta(days=self._retention_days)

        filtered: list[dict[str, Any]] = []
        for entry in entries:
            timestamp = entry.get("timestamp")
            if not timestamp:
                continue
            try:
                entry_time = datetime.fromisoformat(timestamp)
            except ValueError:
                continue
            if entry_time >= cutoff:
                filtered.append(entry)

        if len(filtered) > self._max_records:
            filtered = filtered[-self._max_records :]

        if filtered != entries:
            with self._log_path.open("w", encoding="utf-8") as handle:
                for entry in filtered:
                    handle.write(json.dumps(entry) + "\n")
            # rebuild dedupe cache and indexes
            self._dedupe_cache.clear()
            if self._dedupe_store.exists():
                self._dedupe_store.unlink()
            self._task_index.unlink(missing_ok=True)
            self._reward_index.unlink(missing_ok=True)
            self._policy_index.unlink(missing_ok=True)
            for entry in filtered:
                if self._dedupe_fields:
                    self._dedupe_cache.add(self._fingerprint(entry))
                self._update_indexes(entry)
            if self._dedupe_fields:
                self._persist_dedupe()

    def _redact_mapping(self, mapping: dict[str, Any]) -> dict[str, Any]:
        if not self._redact_fields:
            return mapping
        sanitized = dict(mapping)
        for field in self._redact_fields:
            if field in sanitized:
                sanitized[field] = "[redacted]"
        return sanitized

    def _fingerprint(self, entry: dict[str, Any]) -> str:
        if not self._dedupe_fields:
            return sha256(json.dumps(entry, sort_keys=True).encode("utf-8")).hexdigest()
        values = []
        for field in self._dedupe_fields:
            values.append(
                str(
                    entry["context"].get(field)
                    or entry["edit"].get(field)
                    or entry["metadata"].get(field)
                    or ""
                )
            )
        payload = "|".join(values)
        return sha256(payload.encode("utf-8")).hexdigest()

    def _load_entries(self) -> list[dict[str, Any]]:
        if not self._log_path.exists():
            return []
        lines = self._log_path.read_text(encoding="utf-8").splitlines()
        entries: list[dict[str, Any]] = []
        for line in lines:
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    def _load_index(self, path: Path, default: Any | None = None) -> Any:
        if default is None:
            default = {}
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return default
        return default

    def _write_index(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_state(self) -> None:
        if self._dedupe_store.exists():
            try:
                stored = json.loads(self._dedupe_store.read_text(encoding="utf-8"))
                self._dedupe_cache = set(stored)
            except json.JSONDecodeError:
                self._dedupe_cache = set()

    def _persist_dedupe(self) -> None:
        self._dedupe_store.write_text(json.dumps(list(self._dedupe_cache)), encoding="utf-8")

