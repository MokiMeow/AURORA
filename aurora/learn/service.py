"""Learning service managing nightly adapter updates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class LearningConfig:
    adapters_path: Path
    nightly: bool = False


class LearningService:
    def __init__(self, config: LearningConfig) -> None:
        self._config = config

    def run(self) -> None:
        # TODO: integrate Filtered-SFT pipeline.
        self._config.adapters_path.mkdir(parents=True, exist_ok=True)

