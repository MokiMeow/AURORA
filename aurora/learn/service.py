"""Learning service managing nightly adapter updates."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .config import TrainingConfig
from .hardware import HardwareDetector
from .registry import AdapterRegistry, AdapterInfo
from .pipeline import SFTPipeline
from .federation import FederationSync, FederationConfig
from ..planner.pdca import PDCAEntry

LOGGER = logging.getLogger(__name__)


class LearningService:
    def __init__(self, config: TrainingConfig) -> None:
        self._config = config
        self._registry = AdapterRegistry(config.adapters_path)
        self._hardware_detector = HardwareDetector()

    def run(self, nightly: bool = False, federated: bool = False) -> None:
        PDCAEntry(phase="Learn", event="start", payload={"nightly": nightly}).write()
        hardware = self._hardware_detector.detect()
        LOGGER.info("Using hardware: %s", hardware)
        self._config.output_adapter.parent.mkdir(parents=True, exist_ok=True)
        pipeline = SFTPipeline(
            data_path=self._config.data_path,
            base_model=self._config.base_model,
            output_path=self._config.output_adapter,
            epochs=self._config.epochs,
            learning_rate=self._config.learning_rate,
        )
        result = pipeline.run()
        adapter_info = AdapterInfo(
            name="default",
            version=result.adapter_path.name,
            path=result.adapter_path,
            metadata={
                "name": "default",
                "version": result.adapter_path.name,
                "epochs": self._config.epochs,
                "learning_rate": self._config.learning_rate,
                "bias_score": result.bias_score,
                "metrics": result.training_metrics,
            },
        )
        self._registry.register(adapter_info)
        if result.bias_score > self._config.bias_threshold:
            PDCAEntry(phase="Learn", event="bias_warning", payload={"bias_score": result.bias_score}).write()
        if federated:
            federation = FederationSync(
                FederationConfig(
                    peer="default-peer",
                    encryption_enabled=True,
                    policy_path=Path("policies/security.yaml"),
                )
            )
            federation.sync(result.adapter_path)
        PDCAEntry(phase="Learn", event="complete", payload={"adapter": adapter_info.version}).write()

