"""Autopilot orchestration service."""

from __future__ import annotations

import json
import time
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Sequence

from ..planner.pdca import PDCAEntry
from ..reward.service import RewardService
from ..eval.service import EvaluationService
from ..eval.config_loader import load_evaluation_config
from ..reward import load_reward_config
from ..reward import RewardConfig
from ..session import SessionManager
from ..extensions.manager import ExtensionManager
from ..extensions.base import AuroraExtension
from .config import AutopilotConfig


@dataclass(slots=True)
class AutopilotReport:
    run_id: str
    task: str
    duration_seconds: float
    steps: Sequence[str]
    artifacts: Dict[str, Path]
    estimated_tokens: int


class AutopilotService:
    def __init__(
        self,
        config: AutopilotConfig,
        session_manager: SessionManager | None = None,
    ) -> None:
        self._config = config
        self._session_manager = session_manager or SessionManager(config.session_root)
        self._reward_config: RewardConfig | None = None

    def run(
        self,
        task: str,
        dry_run: bool = False,
        require_confirm: bool = False,
        confirm_callback: callable | None = None,
        max_iterations: int | None = None,
        max_cost: float | None = None,
        seed: int | None = None,
    ) -> AutopilotReport:
        if max_iterations is not None and max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        rng = random.Random(seed)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        session = self._session_manager.start(name=f"autopilot-{task}", description="Autopilot run", metadata={"task": task, "run_id": run_id})
        start = time.perf_counter()
        PDCAEntry(
            phase="Plan",
            event="autopilot_start",
            payload={"task": task, "run_id": run_id, "session": session.id},
        )
        self._load_plugins()
        plan_artifact = self._write_plan_stub(session.path, task)
        steps: list[str] = ["plan"]
        estimated_tokens = rng.randint(140, 260)
        estimated_cost = round(estimated_tokens * 0.00002, 4)
        if max_cost is not None and estimated_cost > max_cost:
            return self._finalize(task, run_id, start, steps, {"plan": plan_artifact}, tokens=estimated_tokens)
        if max_iterations is not None and len(steps) >= max_iterations:
            return self._finalize(task, run_id, start, steps, {"plan": plan_artifact}, tokens=estimated_tokens)
        if require_confirm:
            should_continue = confirm_callback() if confirm_callback else False
            if not should_continue:
                return self._finalize(task, run_id, start, steps, {"plan": plan_artifact}, tokens=estimated_tokens)
        apply_artifact = self._write_apply_stub(session.path, task, dry_run=dry_run)
        steps.append("apply")
        if max_iterations is not None and len(steps) >= max_iterations:
            artifacts = {
                "plan": plan_artifact,
                "apply": apply_artifact,
            }
            return self._finalize(task, run_id, start, steps, artifacts, tokens=estimated_tokens)
        reward_result = self._compute_reward(plan_artifact)
        steps.append("reward")
        if max_cost is not None and (estimated_cost * 1.5) > max_cost:
            artifacts = {
                "plan": plan_artifact,
                "apply": apply_artifact,
                "reward": reward_result,
            }
            return self._finalize(task, run_id, start, steps, artifacts, tokens=estimated_tokens)
        eval_result = self._run_evaluation(dry_run)
        steps.append("evaluation")
        artifacts = {
            "plan": plan_artifact,
            "apply": apply_artifact,
            "reward": reward_result,
            "evaluation": eval_result,
        }
        PDCAEntry(
            phase="Act",
            event="autopilot_complete",
            payload={"task": task, "run_id": run_id, "session": session.id, "artifacts": {k: str(v) for k, v in artifacts.items()}},
        )
        return self._finalize(task, run_id, start, steps, artifacts, tokens=estimated_tokens)

    def _write_plan_stub(self, session_path: Path, task: str) -> Path:
        plan_path = session_path / "plan.json"
        plan_payload = {
            "task": task,
            "steps": ["analyze requirements", "propose changes", "prepare patches"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        plan_path.write_text(json.dumps(plan_payload, indent=2), encoding="utf-8")
        return plan_path

    def _write_apply_stub(self, session_path: Path, task: str, dry_run: bool) -> Path:
        apply_path = session_path / "apply.log"
        log_lines = [
            f"[apply] task={task}",
            f"[apply] dry_run={dry_run}",
            "[apply] no-op changes recorded; integrate executor when available",
        ]
        apply_path.write_text("\n".join(log_lines), encoding="utf-8")
        return apply_path

    def _compute_reward(self, plan_path: Path) -> Path:
        reward_dir = plan_path.parent
        reward_artifact = reward_dir / "reward.json"
        if self._reward_config is None:
            self._reward_config = load_reward_config(Path.cwd(), self._config.reward_config)
        service = RewardService.from_config(self._config.reward_config, root=reward_dir)
        ci_results = [{"step": "plan-review", "success": True}]
        result = service.evaluate(ci_results)
        payload = {
            "reward": result.reward,
            "success": result.success,
            "metrics": result.metrics,
            "reasons": result.reasons,
        }
        reward_artifact.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return reward_artifact

    def _run_evaluation(self, dry_run: bool) -> Path:
        eval_config = load_evaluation_config(self._config.evaluation_config)
        suites = list(eval_config.suites)
        if not suites:
            raise ValueError("No suites configured for evaluation")
        metrics_path = eval_config.results_dir / f"{suites[0]}_autopilot_metrics.json"
        if dry_run:
            payload = {
                "suite": suites[0],
                "run_id": "dry-run",
                "success_rate": 1.0,
                "exit_code": 0,
            }
            metrics_path.parent.mkdir(parents=True, exist_ok=True)
            metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return metrics_path
        service = EvaluationService(eval_config)
        result = service.run(suites[0])
        return result.metrics_path

    def _finalize(
        self,
        task: str,
        run_id: str,
        start: float,
        steps: Sequence[str],
        artifacts: Dict[str, Path],
        tokens: int,
    ) -> AutopilotReport:
        duration = time.perf_counter() - start
        return AutopilotReport(
            run_id=run_id,
            task=task,
            duration_seconds=duration,
            steps=steps,
            artifacts=artifacts,
            estimated_tokens=tokens,
        )

    def _load_plugins(self) -> None:
        if not self._config.plugins:
            return
        manager = ExtensionManager()
        manager.load_many(self._config.plugins)
        for extension in manager.extensions:
            if isinstance(extension, AuroraExtension):
                extension.on_autopilot_start()
