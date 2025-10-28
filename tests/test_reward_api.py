"""Tests for the reward API."""

import json
from pathlib import Path

from aurora.reward import RewardAPI


def test_reward_api_returns_latest_and_summary(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    entries = [
        {"timestamp": "2024-01-01T00:00:00", "reward": 0.5, "success": False},
        {"timestamp": "2024-01-02T00:00:00", "reward": 1.2, "success": True},
    ]
    with history_path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")

    api = RewardAPI(history_path)
    latest = api.latest()
    assert latest["reward"] == 1.2

    summary = api.summary()
    assert summary["count"] == 2
    assert summary["success_rate"] == 0.5
