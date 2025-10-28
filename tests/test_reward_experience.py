"""Tests for the reward experience logger."""

import json
from pathlib import Path

from aurora.reward import ExperienceLogger, ExperienceRecord


def test_experience_logger_deduplicates_and_indexes(tmp_path: Path) -> None:
    log_path = tmp_path / "reward.log.jsonl"
    index_root = tmp_path / "indices"
    logger = ExperienceLogger(
        log_path=log_path,
        index_root=index_root,
        dedupe_fields=("task", "diff_hash"),
        redact_fields=("secret",),
    )

    record = ExperienceRecord(
        context={"task": "TASK-1", "secret": "keep"},
        edit={"summary": "initial patch"},
        telemetry={"policy": ["ok"]},
        reward=1.5,
        regret=False,
        metadata={"diff_hash": "abc123"},
    )
    logger.append(record)
    logger.append(record)  # dedupe

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    task_index = json.loads((index_root / "task_index.json").read_text(encoding="utf-8"))
    assert "TASK-1" in task_index

    reward_index = json.loads((index_root / "top_rewards.json").read_text(encoding="utf-8"))
    assert reward_index[0]["reward"] == 1.5
    entry = json.loads(lines[0])
    assert entry["context"]["secret"] == "[redacted]"
