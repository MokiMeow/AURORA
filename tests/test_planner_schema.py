"""Tests for planner schema validation."""

import pytest
from pydantic import ValidationError

from aurora.planner.schema import SelfEdit


def test_self_edit_schema_requires_adapter_when_training_enabled():
    payload = {
        "intent": "bugfix",
        "summary": "Fix issue",
        "plan": ["step"],
        "graph_targets": ["file.py"],
        "patches": [{"path": "file.py", "diff": "---"}],
        "tests": [{"path": "tests/test_file.py", "content": ""}],
        "tools": {},
        "train": {"enable": True},
        "acceptance": {"min_R": 0.0, "security_zero_criticals": True},
    }
    with pytest.raises(ValidationError):
        SelfEdit.model_validate(payload)


def test_self_edit_schema_accepts_valid_payload():
    payload = {
        "intent": "bugfix",
        "summary": "Fix issue",
        "plan": ["step"],
        "graph_targets": ["file.py"],
        "patches": [{"path": "file.py", "diff": "---"}],
        "tests": [{"path": "tests/test_file.py", "content": ""}],
        "tools": {},
        "train": {"enable": True, "adapter_id": "adapter-1"},
        "acceptance": {"min_R": 0.0, "security_zero_criticals": True},
    }
    self_edit = SelfEdit.model_validate(payload)
    assert self_edit.train.adapter_id == "adapter-1"

