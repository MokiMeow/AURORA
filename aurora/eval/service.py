"""Evaluation service for running SWE-Bench suites and logging results."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..planner.pdca import PDCAEntry
from .analytics import export_metrics_csv, generate_dashboard
from .config import EvaluationConfig, SuiteConfig
from .dataset_manager import DatasetManager
from .analytics import diff_sbom
from ..governance.bundle import assemble_bundle
from ..governance.compliance import CompliancePolicy

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class EvaluationResult:
    suite: str
    exit_code: int
    output_path: Path
    metrics_path: Path
    compliance_path: Path
    sbom_path: Optional[Path]
    telemetry_path: Optional[Path]


class EvaluationService:
    def __init__(self, config: EvaluationConfig) -> None:
        self._config = config
        self._dataset_manager = DatasetManager(config.dataset_manager)
        self._compliance_policy = CompliancePolicy(max_bias_score=0.2)

    def run(self, suite_name: str) -> EvaluationResult:
        if suite_name not in self._config.suites:
            raise ValueError(f"Unknown evaluation suite {suite_name}")
        suite = self._config.suites[suite_name]
        self._dataset_manager.ensure(suite)
        suite.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._config.results_dir.mkdir(parents=True, exist_ok=True)
        run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        PDCAEntry(
            phase="Check",
            event="evaluation_start",
            payload={
                "suite": suite_name,
                "schedule": suite.schedule,
                "profile": suite.profile,
                "run_id": run_id,
                "scenarios": suite.scenarios,
            },
        )
        result_path = suite.artifacts_dir / f"{suite_name}_{run_id}_raw.json"
        metrics_path = self._config.results_dir / f"{suite_name}_{run_id}_metrics.json"
        compliance_path = suite.artifacts_dir / f"{suite_name}_{run_id}_compliance.json"
        process = subprocess.run(
            suite.command,
            cwd=suite.dataset_path,
            capture_output=True,
            text=True,
            timeout=suite.timeout_minutes * 60,
        )
        raw_result = {
            "suite": suite_name,
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "profile": suite.profile,
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        result_path.write_text(json.dumps(raw_result, indent=2), encoding="utf-8")
        metrics = self._compute_metrics(raw_result, suite)
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        sbom_path = self._generate_sbom_snapshot(suite, run_id)
        telemetry_path = self._write_telemetry_snapshot(suite, raw_result, metrics)
        compliance_report = self._build_compliance_report(suite, metrics, sbom_path, telemetry_path)
        compliance_path.write_text(json.dumps(compliance_report, indent=2), encoding="utf-8")

        export_metrics_csv(self._config.results_dir, self._config.analytics.metrics_csv)
        generate_dashboard(self._config.results_dir, self._config.analytics.dashboard_html)
        self._diff_sbom(suite, sbom_path)
        issues = self._evaluate_compliance(compliance_report)
        PDCAEntry(
            phase="Check",
            event="evaluation_complete",
            payload={
                "suite": suite_name,
                "exit_code": process.returncode,
                "metrics": metrics,
                "compliance": compliance_report,
                "run_id": run_id,
                "planner_version": self._planner_version(),
                "executor_version": self._executor_version(),
                "reward_stats": self._reward_snapshot(),
                "compliance_issues": issues,
            },
        )
        self._dataset_manager.record_result(suite, run_id, metrics)
        self._publish_governance_bundle(suite, compliance_report, issues)
        return EvaluationResult(
            suite=suite_name,
            exit_code=process.returncode,
            output_path=result_path,
            metrics_path=metrics_path,
            compliance_path=compliance_path,
            sbom_path=sbom_path,
            telemetry_path=telemetry_path,
        )

    def _compute_metrics(self, raw_result: dict[str, Any], suite: SuiteConfig) -> dict[str, Any]:
        stdout = raw_result.get("stdout", "")
        metrics: dict[str, Any] = {
            "suite": raw_result.get("suite"),
            "profile": raw_result.get("profile"),
            "run_id": raw_result.get("run_id"),
            "exit_code": raw_result.get("exit_code"),
            "timestamp": raw_result.get("timestamp"),
        }
        for line in stdout.splitlines():
            if line.startswith("METRIC:"):
                try:
                    key, value = line.split("METRIC:", 1)[1].split("=", 1)
                    metrics[key.strip()] = float(value)
                except (ValueError, IndexError):
                    LOGGER.debug("Failed to parse metric line: %s", line)
            elif "=" in line and line.split("=", 1)[0].isupper():
                key, value = line.split("=", 1)
                metrics[key.lower()] = self._coerce_number(value.strip())
        metrics.setdefault("success_rate", 1.0 if raw_result.get("exit_code") == 0 else 0.0)
        metrics.setdefault("failures", 0 if raw_result.get("exit_code") == 0 else 1)
        metrics["baseline"] = str(suite.baseline_metrics) if suite.baseline_metrics else None
        metrics["compare_against"] = suite.compare_against
        return metrics

    @staticmethod
    def _coerce_number(value: str) -> Any:
        try:
            if value.isdigit():
                return int(value)
            return float(value)
        except ValueError:
            return value

    def _build_compliance_report(
        self,
        suite: SuiteConfig,
        metrics: dict[str, Any],
        sbom_path: Optional[Path],
        telemetry_path: Optional[Path],
    ) -> dict[str, Any]:
        return {
            "suite": suite.name,
            "profile": suite.profile,
            "schedule": suite.schedule,
            "metrics": metrics,
            "sbom": str(sbom_path) if sbom_path else None,
            "telemetry": str(telemetry_path) if telemetry_path else None,
            "postprocessors": suite.postprocessors,
        }

    def _generate_sbom_snapshot(self, suite: SuiteConfig, run_id: str) -> Optional[Path]:
        sbom_dir = suite.artifacts_dir / "sbom"
        sbom_dir.mkdir(parents=True, exist_ok=True)
        sbom_path = sbom_dir / f"{suite.name}_{run_id}.json"
        sbom_payload = {
            "suite": suite.name,
            "run_id": run_id,
            "generated_at": datetime.utcnow().isoformat(),
        }
        sbom_path.write_text(json.dumps(sbom_payload, indent=2), encoding="utf-8")
        return sbom_path

    def _write_telemetry_snapshot(self, suite: SuiteConfig, raw_result: dict[str, Any], metrics: dict[str, Any]) -> Optional[Path]:
        telemetry_dir = suite.artifacts_dir / "telemetry"
        telemetry_dir.mkdir(parents=True, exist_ok=True)
        telemetry_path = telemetry_dir / f"{suite.name}_{raw_result['run_id']}.jsonl"
        entry = json.dumps({"raw": raw_result, "metrics": metrics}, ensure_ascii=False)
        telemetry_path.write_text(entry + "\n", encoding="utf-8")
        return telemetry_path

    def _diff_sbom(self, suite: SuiteConfig, current: Optional[Path]) -> None:
        if not current:
            return
        sbom_dir = suite.artifacts_dir / "sbom"
        previous_files = sorted(sbom_dir.glob(f"{suite.name}_*.json"))
        prev = previous_files[-2] if len(previous_files) > 1 else None
        compare_dir = self._config.analytics.compare_dir
        compare_dir.mkdir(parents=True, exist_ok=True)
        output = compare_dir / f"{suite.name}_sbom_diff.json"
        diff_sbom(prev, current, output)

    def _planner_version(self) -> str:
        return "main"

    def _executor_version(self) -> str:
        return "main"

    def _reward_snapshot(self) -> dict[str, Any]:
        reward_log = Path("artifacts/reward_reports/latest_reward.json")
        if reward_log.exists():
            try:
                return json.loads(reward_log.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def _evaluate_compliance(self, report: dict[str, Any]) -> list[str]:
        return self._compliance_policy.evaluate(report)

    def _publish_governance_bundle(self, suite: SuiteConfig, report: dict[str, Any], issues: list[str]) -> None:
        bundle_path = Path("docs/governance/bundles") / f"{suite.name}_latest.json"
        assemble_bundle(bundle_path, report, overrides=[{"issues": issues}] if issues else None)
