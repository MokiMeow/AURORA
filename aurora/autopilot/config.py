"""Autopilot configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(slots=True)
class AutopilotConfig:
    session_root: Path
    plan_config: Path
    executor_config: Path
    reward_config: Path
    evaluation_config: Path
    plugins: Sequence[str] = ()
