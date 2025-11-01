"""Interactive shell implementation with autopilot and governance shortcuts."""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List

from ..autopilot import AutopilotReport, AutopilotService
from ..executor.policy import PolicyEvaluator
from ..extensions.registry import ExtensionRegistry
from ..planner import ModelManager
from ..reward.service import RewardService
from ..session import Session, SessionManager
from ..workspace import WorkspaceManager


@dataclass(slots=True)
class ShellContext:
    approvals: dict[str, bool] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    model: str | None = None
    critic_enabled: bool = False
    active_session: Session | None = None


class ShellSession:
    """Implements `/` commands documented in plan.md."""

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        autopilot_service: AutopilotService | None = None,
        model_manager: ModelManager | None = None,
        workspace_manager: WorkspaceManager | None = None,
        extension_registry: ExtensionRegistry | None = None,
        reward_service: RewardService | None = None,
        policy_evaluator: PolicyEvaluator | None = None,
        telemetry_log: Path | None = None,
        extensions_config: Path | None = None,
    ) -> None:
        self._session_manager = session_manager or SessionManager()
        self._autopilot = autopilot_service
        self._model_manager = model_manager
        self._workspace_manager = workspace_manager or WorkspaceManager()
        self._registry = extension_registry or ExtensionRegistry()
        self._reward_service = reward_service
        self._policy_evaluator = policy_evaluator
        self._telemetry_log = telemetry_log or Path("telemetry/errors.jsonl")
        self._extensions_config = extensions_config or Path("configs/extensions.txt")
        self._context = ShellContext()

    def run(self, commands: Iterable[str] | None = None, output: Callable[[str], None] | None = None) -> None:
        output = output or print
        iterator = iter(commands) if commands is not None else None
        output("Aurora-SE interactive shell (type 'exit' to leave)")
        while True:
            cmd = next(iterator) if iterator is not None else input("aurora> ")
            cmd = cmd.strip()
            if not cmd:
                continue
            if cmd in {"exit", "quit", "/quit"}:
                output("bye!")
                break
            if cmd.startswith("/"):
                self._handle_slash(cmd, output)
            else:
                self._stream_response(f"Echo: {cmd}", output)

    # Slash command handlers -------------------------------------------------

    def _handle_slash(self, cmd: str, output: Callable[[str], None]) -> None:
        parts = shlex.split(cmd)
        command = parts[0]
        args = parts[1:]

        if command == "/context":
            output(self._render_context())
        elif command == "/allow":
            key = args[0] if args else "default"
            self._context.approvals[key] = True
            output(f"allow set for {key}")
        elif command == "/deny":
            key = args[0] if args else "default"
            self._context.approvals[key] = False
            output(f"deny set for {key}")
        elif command == "/help":
            output(self._help_text())
        elif command == "/model":
            self._handle_model(args, output)
        elif command == "/critic":
            self._handle_critic(args, output)
        elif command == "/session":
            self._handle_session(args, output)
        elif command == "/workspace":
            self._handle_workspace(args, output)
        elif command == "/autopilot":
            self._handle_autopilot(args, output)
        elif command == "/plugin":
            self._handle_plugin(args, output)
        elif command == "/logs":
            self._handle_logs(args, output)
        elif command == "/reward":
            self._handle_reward(args, output)
        elif command == "/policy":
            self._handle_policy(args, output)
        else:
            output(f"Unknown command {command}. Type /help for options.")

    def _handle_model(self, args: list[str], output: Callable[[str], None]) -> None:
        if not self._model_manager:
            output("Model manager unavailable.")
            return
        if not args:
            output("Usage: /model <profile>")
            return
        profile = args[0]
        try:
            self._model_manager.switch(profile)
            self._context.model = profile
            output(f"Model profile switched to {profile}")
        except Exception as exc:  # pragma: no cover - defensive
            output(f"Failed to switch model: {exc}")

    def _handle_critic(self, args: list[str], output: Callable[[str], None]) -> None:
        if not args:
            output("Usage: /critic on|off")
            return
        state = args[0].lower()
        self._context.critic_enabled = state == "on"
        output(f"Critic stack {'enabled' if self._context.critic_enabled else 'disabled'}")

    def _handle_session(self, args: list[str], output: Callable[[str], None]) -> None:
        if not args:
            output("Usage: /session save|load <name>")
            return
        action = args[0]
        if action == "save":
            name = args[1] if len(args) > 1 else "shell-session"
            session = self._session_manager.start(name=name, description="Shell snapshot")
            self._context.active_session = session
            output(f"Session saved with id {session.id}")
        elif action == "load":
            if len(args) < 2:
                output("Usage: /session load <id>")
                return
            session = self._session_manager.resume(args[1])
            self._context.active_session = session
            output(f"Session {session.id} loaded.")
        else:
            output("Usage: /session save|load <name>")

    def _handle_workspace(self, args: list[str], output: Callable[[str], None]) -> None:
        if not args:
            output("Usage: /workspace snapshot|restore [tag]")
            return
        action = args[0]
        manager = self._workspace_manager
        if action == "snapshot":
            tag = args[1] if len(args) > 1 else None
            snapshot = manager.snapshot(tag=tag)
            output(f"Snapshot {snapshot.tag} -> {snapshot.archive_path}")
        elif action == "restore":
            if len(args) < 2:
                output("Usage: /workspace restore <tag>")
                return
            manager.restore(tag=args[1])
            output(f"Snapshot {args[1]} restored.")
        else:
            output("Usage: /workspace snapshot|restore [tag]")

    def _handle_autopilot(self, args: list[str], output: Callable[[str], None]) -> None:
        if not self._autopilot:
            output("Autopilot service unavailable.")
            return
        if not args:
            output("Usage: /autopilot <task>")
            return
        task = " ".join(args)
        report = self._autopilot.run(task=task, dry_run=True)
        summary = {
            "run_id": report.run_id,
            "steps": list(report.steps),
            "artifacts": {k: str(v) for k, v in report.artifacts.items()},
        }
        output(json.dumps(summary, indent=2))

    def _handle_plugin(self, args: list[str], output: Callable[[str], None]) -> None:
        if not args:
            output("Usage: /plugin list|enable|disable <spec>")
            return
        action = args[0]
        specs = set(self._read_extension_specs())
        if action == "list":
            entries = self._registry.list()
            if not entries and not specs:
                output("No plugins registered.")
                return
            for manifest in entries:
                output(f"{manifest.name} -> {manifest.spec}")
            for spec in specs:
                output(f"config: {spec}")
        elif action in {"enable", "disable"}:
            if len(args) < 2:
                output(f"Usage: /plugin {action} <spec>")
                return
            spec = args[1]
            if action == "enable":
                specs.add(spec)
                output(f"Enabled {spec}")
            else:
                if spec in specs:
                    specs.remove(spec)
                    output(f"Disabled {spec}")
                else:
                    output(f"{spec} not active.")
            self._write_extension_specs(sorted(specs))
        else:
            output("Usage: /plugin list|enable|disable <spec>")

    def _handle_logs(self, args: list[str], output: Callable[[str], None]) -> None:
        tail = 10
        if args and args[0] == "--tail" and len(args) > 1:
            tail = int(args[1])
        if not self._telemetry_log.exists():
            output(f"No telemetry log at {self._telemetry_log}")
            return
        lines = self._telemetry_log.read_text(encoding="utf-8").splitlines()
        for line in lines[-tail:]:
            output(line)

    def _handle_reward(self, args: list[str], output: Callable[[str], None]) -> None:
        if not self._reward_service:
            output("Reward service unavailable.")
            return
        artifact = self._reward_service.render_explainability()
        payload = json.loads(artifact.read_text(encoding="utf-8")) if artifact.exists() else {}
        output(json.dumps(payload, indent=2) if payload else "No reward artifact generated yet.")

    def _handle_policy(self, args: list[str], output: Callable[[str], None]) -> None:
        if not self._policy_evaluator:
            output("Policy evaluator unavailable.")
            return
        payload = [{"step": "shell", "success": True}]
        outcome = self._policy_evaluator.evaluate(payload)
        output(json.dumps({"accepted": outcome.accepted, "reasons": outcome.reasons}, indent=2))

    # Helpers ----------------------------------------------------------------

    def _render_context(self) -> str:
        approvals = ", ".join(
            f"{k}:{'allow' if v else 'deny'}" for k, v in self._context.approvals.items()
        ) or "(none)"
        session_id = self._context.active_session.id if self._context.active_session else "(none)"
        return (
            f"Approvals -> {approvals}\n"
            f"Model -> {self._context.model or '(default)'}\n"
            f"Critic -> {'on' if self._context.critic_enabled else 'off'}\n"
            f"Session -> {session_id}\n"
            f"Notes: {len(self._context.notes)} entries"
        )

    @staticmethod
    def _stream_response(message: str, output: Callable[[str], None]) -> None:
        chunks = [message[i : i + 20] for i in range(0, len(message), 20)]
        for chunk in chunks:
            output(chunk)

    @staticmethod
    def _help_text() -> str:
        return (
            "Commands: /context, /model <name>, /critic on|off, /allow <tag>, /deny <tag>, "
            "/session save|load <id>, /workspace snapshot|restore <tag>, /autopilot <task>, "
            "/plugin list|enable|disable <spec>, /logs [--tail N], /reward [--explain], "
            "/policy check, /help, /quit"
        )

    def _read_extension_specs(self) -> list[str]:
        if not self._extensions_config.exists():
            return []
        data = []
        for line in self._extensions_config.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            data.append(line)
        return data

    def _write_extension_specs(self, specs: list[str]) -> None:
        self._extensions_config.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(specs)
        if content:
            content += "\n"
        self._extensions_config.write_text(content, encoding="utf-8")
