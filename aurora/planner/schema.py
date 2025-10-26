"""Schema definitions for Self-Edit plans."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


IntentType = Literal[
    "feature",
    "bugfix",
    "refactor",
    "security",
    "performance",
    "maintenance",
]


class Patch(BaseModel):
    path: str = Field(..., description="Relative file path to modify")
    diff: str = Field(..., description="Unified diff patch")


class TestCase(BaseModel):
    path: str = Field(..., description="Relative path for the test file")
    content: str = Field(..., description="Test code content or reference")


class ToolInvocation(BaseModel):
    lint: dict = Field(default_factory=dict)
    typecheck: dict = Field(default_factory=dict)
    static_analysis: dict = Field(default_factory=dict)
    fuzz: dict = Field(default_factory=dict)
    perf: dict = Field(default_factory=dict)


class TrainConfig(BaseModel):
    enable: bool = False
    adapter_id: str | None = None
    lr: float = 1e-4
    epochs: int = 2

    @model_validator(mode="after")
    def ensure_adapter_when_enabled(self) -> "TrainConfig":
        if self.enable and not self.adapter_id:
            msg = "adapter_id required when training is enabled"
            raise ValueError(msg)
        return self


class AcceptanceCriteria(BaseModel):
    min_R: float = Field(0.0, description="Minimum reward threshold for acceptance")
    perf_thresholds: dict = Field(default_factory=dict)
    security_zero_criticals: bool = True


class SelfEdit(BaseModel):
    intent: IntentType
    summary: str
    plan: list[str]
    graph_targets: list[str]
    patches: list[Patch]
    tests: list[TestCase]
    tools: ToolInvocation
    train: TrainConfig
    acceptance: AcceptanceCriteria

    model_config = {
        "json_schema_extra": {
            "example": {
                "intent": "bugfix",
                "summary": "Fix failing login test",
                "plan": ["Inspect failing test", "Update auth logic", "Add regression test"],
                "graph_targets": ["auth/login.py", "tests/test_login.py"],
                "patches": [
                    {
                        "path": "auth/login.py",
                        "diff": "--- a/auth/login.py\n+++ b/auth/login.py\n@@",
                    }
                ],
                "tests": [
                    {
                        "path": "tests/test_login.py",
                        "content": "# test placeholder",
                    }
                ],
                "tools": {},
                "train": {"enable": False},
                "acceptance": {"min_R": 0.0, "security_zero_criticals": True},
            }
        }
    }

