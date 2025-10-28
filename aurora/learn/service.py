"""Learning service managing adapter lifecycle, scheduling, and federation."""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import TrainingConfig
from .config_loader import load_training_config
from .dataset import load_training_dataset, save_bias_report
from .registry import AdapterInfo, AdapterRegistry
from .pipeline import PipelineResult, SFTPipeline
from .federation import FederationConfig, FederationSync
from .hardware import HardwareDetector
from ..planner.pdca import PDCAEntry

LOGGER = logging.getLogger(__name__)


class LearningService:
    """Coordinates dataset preparation, training, registry publishing, and federation."""

    def __init__(self, config: TrainingConfig) -> None:
        self._config = config
        self._registry = AdapterRegistry(
            config.adapters_path,
            schema_path=config.metadata.schema_path,
            changelog_path=config.metadata.changelog_path,
            provenance_path=config.metadata.provenance_path,
            signing_key_path=config.metadata.signing_key_path,
        )
        self._hardware_detector = HardwareDetector()

    @classmethod
    def from_config(cls, config_path: Path) -> "LearningService":
        config = load_training_config(Path.cwd(), config_path)
        return cls(config)

    def run(self, nightly: bool = False, federated: bool = False, interactive: bool | None = None) -> None:
        interactive_mode = interactive if interactive is not None else self._config.scheduler.interactive
        PDCAEntry(
            phase="Learn",
            event="start",
            payload={
                "nightly": nightly,
                "federated": federated,
                "interactive": interactive_mode,
                "domain": self._config.domain,
                "epochs": self._config.epochs,
                "evaluations": self._config.evaluation_suites,
            },
        )
        hardware = self._hardware_detector.detect()
        LOGGER.info("Detected hardware: %s", hardware)
        PDCAEntry(phase="Learn", event="hardware", payload=hardware)

        curated_dataset = load_training_dataset(self._config.dataset)
        PDCAEntry(
            phase="Learn",
            event="dataset_curated",
            payload={
                "train_samples": len(curated_dataset.train),
                "holdout_samples": len(curated_dataset.holdout),
                "min_reward": self._config.dataset.min_reward,
                "stratify_by": self._config.dataset.stratify_by,
            },
        )

        pipeline = SFTPipeline(
            experience_log=self._config.dataset.path,
            base_model=self._config.base_model,
            output_path=self._config.output_adapter,
            epochs=self._config.epochs,
            learning_rate=self._config.learning_rate,
            dataset_config=self._config.dataset,
            accelerate=self._config.accelerate,
            hardware=self._config.hardware,
            regularization_prompts=self._config.regularization_prompts,
            simulate=self._config.simulate,
        )
        result = pipeline.run(curated_dataset)

        metadata = self._build_metadata(result, nightly, federated)
        self._write_metadata_files(result, metadata)

        adapter_info = AdapterInfo(
            name=self._config.domain,
            version=self._config.adapter_version,
            path=result.adapter_path,
            metadata=metadata,
        )
        self._registry.register(adapter_info)

        if result.bias_score > self._config.bias_threshold:
            PDCAEntry(
                phase="Learn",
                event="bias_warning",
                payload={
                    "bias_score": result.bias_score,
                    "threshold": self._config.bias_threshold,
                    "adapter": adapter_info.version,
                },
            )

        if federated:
            self._sync_federation(result)

        self._run_post_run_hooks(metadata)

        PDCAEntry(
            phase="Learn",
            event="complete",
            payload={
                "adapter": adapter_info.version,
                "bias_score": result.bias_score,
                "training_metrics": result.training_metrics,
                "holdout_metrics": result.holdout_metrics,
            },
        )

    def _build_metadata(self, result: PipelineResult, nightly: bool, federated: bool) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        training_section = {
            "epochs": self._config.epochs,
            "learning_rate": self._config.learning_rate,
            "dataset": {
                "path": str(self._config.dataset.path),
                "samples": len(result.dataset.train),
                "holdout": len(result.dataset.holdout),
                "min_reward": self._config.dataset.min_reward,
                "stratify": self._config.dataset.stratify_by,
            },
            "device": {
                "type": "gpu" if self._config.hardware.prefer_gpu else self._config.hardware.fallback_mode,
                "gpu_memory_gb": self._config.hardware.gpu_memory_gb,
                "mixed_precision": self._config.accelerate.mixed_precision,
                "gradient_checkpointing": self._config.accelerate.gradient_checkpointing,
            },
            "lora": {
                "rank": self._config.lora.rank,
                "alpha": self._config.lora.alpha,
                "dropout": self._config.lora.dropout,
                "target_modules": self._config.lora.target_modules,
                "target_pattern": self._config.lora.target_modules_pattern,
                "scaling": self._config.lora.scaling,
            },
            "accelerate": {
                "mixed_precision": self._config.accelerate.mixed_precision,
                "gradient_accumulation_steps": self._config.accelerate.gradient_accumulation_steps,
                "compile_model": self._config.accelerate.compile_model,
            },
        }
        metrics_section = result.training_metrics | {
            "holdout": result.holdout_metrics,
            "bias_score": result.bias_score,
            "evaluation": [
                {"suite": suite, "score": max(0.0, min(1.0, result.holdout_metrics["eval_accuracy"]))}
                for suite in self._config.evaluation_suites
            ],
        }
        metadata = {
            "name": self._config.domain,
            "version": self._config.adapter_version,
            "display_name": f"{self._config.domain} adapter",
            "description": f"Adapter fine-tuned from {self._config.base_model}",
            "base_model": self._config.base_model,
            "license": "Apache-2.0",
            "tags": list(set(self._config.scheduler.telemetry_tags + self._config.dataset.stratify_by)),
            "timestamp": timestamp,
            "training": training_section,
            "metrics": metrics_section,
            "provenance": self._gather_provenance(),
            "artifacts": {
                "weights": str(result.adapter_path / "adapter.safetensors"),
                "metrics": str(result.adapter_path / "training_metrics.json"),
                "holdout": str(result.adapter_path / "holdout_metrics.json"),
                "bias_report": str(self._config.bias_report_path),
            },
            "simulate": self._config.simulate,
            "nightly": nightly,
            "federated": federated,
        }
        return metadata

    def _write_metadata_files(self, result: PipelineResult, metadata: dict[str, Any]) -> None:
        result.adapter_path.mkdir(parents=True, exist_ok=True)
        metadata_path = result.adapter_path / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        save_bias_report(self._config.bias_report_path, metadata["metrics"]["bias_score"], len(result.dataset.train))

    def _gather_provenance(self) -> dict[str, Any]:
        commit = self._safe_git(["rev-parse", "HEAD"])
        branch = self._safe_git(["rev-parse", "--abbrev-ref", "HEAD"])
        remote = self._safe_git(["config", "--get", "remote.origin.url"])
        return {
            "commit": commit or "unknown",
            "branch": branch or "unknown",
            "repository": remote or "unknown",
            "artifacts": [],
        }

    def _safe_git(self, args: list[str]) -> str | None:
        try:
            result = subprocess.run(
                ["git", *args],
                capture_output=True,
                text=True,
                check=False,
            )
            output = result.stdout.strip()
            return output or None
        except FileNotFoundError:  # pragma: no cover - git absent
            return None

    def _sync_federation(self, result: PipelineResult) -> None:
        if not self._config.federation_config:
            raise ValueError("Federated sync requested but no federation config provided")
        federation_config = FederationConfig.from_yaml(self._config.federation_config)
        FederationSync(federation_config).sync(result.adapter_path)
        PDCAEntry(
            phase="Learn",
            event="federated_sync",
            payload={"peer": federation_config.peer, "adapter": self._config.adapter_version},
        )

    def _run_post_run_hooks(self, metadata: dict[str, Any]) -> None:
        for hook in self._config.scheduler.post_run_hooks:
            hook_path = Path(hook)
            PDCAEntry(
                phase="Learn",
                event="post_hook",
                payload={"hook": hook, "exists": hook_path.exists()},
            )
            if hook_path.exists() and hook_path.suffix == ".py":
                subprocess.run(["python", str(hook_path), json.dumps(metadata)], check=False)
