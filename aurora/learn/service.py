"""Learning service managing nightly adapter updates."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from .config import TrainingConfig
from .hardware import HardwareDetector
from .registry import AdapterRegistry, AdapterInfo
from ..planner.pdca import PDCAEntry

LOGGER = logging.getLogger(__name__)


class LearningService:
    def __init__(self, config: TrainingConfig) -> None:
        self._config = config
        self._registry = AdapterRegistry(config.adapters_path)
        self._hardware_detector = HardwareDetector()

    def run(self, nightly: bool = False) -> None:
        PDCAEntry(phase="Learn", event="start", payload={"nightly": nightly}).write()
        hardware = self._hardware_detector.detect()
        LOGGER.info("Using hardware: %s", hardware)
        self._config.output_adapter.parent.mkdir(parents=True, exist_ok=True)
        # Placeholder training logic
        adapter_info = AdapterInfo(
            name="default",
            version="0.1.0",
            path=self._config.output_adapter,
            metadata={
                "name": "default",
                "version": "0.1.0",
                "epochs": self._config.epochs,
                "learning_rate": self._config.learning_rate,
                "bias_threshold": self._config.bias_threshold,
            },
        )
        self._registry.register(adapter_info)
        PDCAEntry(phase="Learn", event="complete", payload={"adapter": adapter_info.version}).write()

