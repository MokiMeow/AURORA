"""Learning service managing nightly adapter updates."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .config import TrainingConfig
from .config_loader import load_training_config
from .registry import AdapterRegistry, AdapterInfo
from .pipeline import SFTPipeline
from .federation import FederationSync, FederationConfig
from .hardware import HardwareDetector
from ..planner.pdca import PDCAEntry

LOGGER = logging.getLogger(__name__)


class LearningService:
    def __init__(self, config: TrainingConfig) -> None:
        self._config = config
        self._registry = AdapterRegistry(config.adapters_path)
        self._hardware_detector = HardwareDetector()

    @classmethod
    def from_config(cls, config_path: Path) -> "LearningService":
        config = load_training_config(Path.cwd(), config_path)
        return cls(config)

    def run(self, nightly: bool = False, federated: bool = False) -> None:
        PDCAEntry(
            phase="Learn",
            event="start",
            payload={
                "nightly": nightly,
                "federated": federated,
                "domain": self._config.domain,
                "epochs": self._config.epochs,
            },
        ).write()
        hardware = self._hardware_detector.detect()
        LOGGER.info("Using hardware: %s", hardware)
        self._config.output_adapter.parent.mkdir(parents=True, exist_ok=True)
        PDCAEntry(phase="Learn", event="hardware", payload=hardware).write()
        pipeline = SFTPipeline(
            data_path=self._config.data_path,
            base_model=self._config.base_model,
            output_path=self._config.output_adapter,
            epochs=self._config.epochs,
            learning_rate=self._config.learning_rate,
            simulate=self._config.simulate,
            lora_config={
                "rank": self._config.lora.rank,
                "alpha": self._config.lora.alpha,
                "dropout": self._config.lora.dropout,
                "target_modules": self._config.lora.target_modules,
            },
            sample_size=self._config.sample_size,
            regularization_prompts=self._config.regularization_prompts,
            min_reward=self._config.min_reward,
        )
        result = pipeline.run()
        adapter_info = AdapterInfo(
            name=self._config.domain,
            version=result.adapter_path.name,
            path=result.adapter_path,
            metadata={
                "name": self._config.domain,
                "version": result.adapter_path.name,
                "base_model": self._config.base_model,
                "epochs": self._config.epochs,
                "learning_rate": self._config.learning_rate,
                "bias_score": result.bias_score,
                "metrics": result.training_metrics,
                "lora": {
                    "rank": self._config.lora.rank,
                    "alpha": self._config.lora.alpha,
                    "dropout": self._config.lora.dropout,
                    "target_modules": self._config.lora.target_modules,
                },
                "sample_size": self._config.sample_size,
                "min_reward": self._config.min_reward,
                "simulate": self._config.simulate,
            },
        )
        self._registry.register(adapter_info)
        self._write_bias_report(result.training_metrics, result.bias_score)
        if result.bias_score > self._config.bias_threshold:
            PDCAEntry(
                phase="Learn",
                event="bias_warning",
                payload={
                    "bias_score": result.bias_score,
                    "threshold": self._config.bias_threshold,
                    "adapter": adapter_info.version,
                },
            ).write()
        if federated:
            if not self._config.federation_config:
                raise ValueError("Federated sync requested but no federation config provided")
            federation_config = FederationConfig.from_yaml(self._config.federation_config)
            FederationSync(federation_config).sync(result.adapter_path)
            PDCAEntry(
                phase="Learn",
                event="federated_sync",
                payload={"peer": federation_config.peer, "adapter": adapter_info.version},
            ).write()
        PDCAEntry(
            phase="Learn",
            event="complete",
            payload={
                "adapter": adapter_info.version,
                "bias_score": result.bias_score,
                "metrics": result.training_metrics,
            },
        ).write()

    def _write_bias_report(self, metrics: dict[str, Any], bias_score: float) -> None:
        report_path = self._config.bias_report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps({"bias_score": bias_score, "metrics": metrics}), encoding="utf-8")

