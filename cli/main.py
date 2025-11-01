"""Command-line interface for AURORA-SE."""

from __future__ import annotations

import asyncio
import json
import random
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

import typer
import yaml

from aurora import __version__
from aurora.indexer.config_loader import load_indexer_config
from aurora.indexer.store import GraphStore
from aurora.indexer.tree import TreeSitterParser
from aurora.indexer.embedding import EmbeddingStore
from aurora.indexer.service import IndexJobConfig, IndexerService
from aurora.planner.service import PlannerService
from aurora.executor.config_loader import load_executor_config
from aurora.executor import ExecutorService, CIOrchestrator, LocalSandbox
from aurora.executor.sandbox import (
    DockerSandbox,
    FirecrackerNetwork,
    FirecrackerResources,
    FirecrackerSandbox,
    SandboxRunner,
    build_mounts,
)
from aurora.security.secrets import SecretScanner, load_secret_scanner_config
from aurora.executor.policy import PolicyEvaluator
from aurora.learn.config_loader import load_training_config
from aurora.learn.service import LearningService
from aurora.learn.federation import FederationConfig
from aurora.eval.analytics import generate_dashboard, load_metrics
from aurora.eval.compare import compare_metrics
from aurora.eval.config_loader import load_evaluation_config
from aurora.eval.service import EvaluationService
from aurora.learn.cli import list_adapters, publish_adapter, rollback_adapter, sync_adapter
from aurora.telemetry.errors import ErrorLogger
from aurora.telemetry.service import TelemetryService
from aurora.reward.service import RewardService
from aurora.reward import RewardResult
from aurora.cli.shell import ShellSession
from aurora.session import SessionManager
from aurora.autopilot import AutopilotConfig, AutopilotReport, AutopilotService
from aurora.extensions.manager import ExtensionManager
from aurora.extensions.registry import ExtensionRegistry
from aurora.workspace import WorkspaceManager
from aurora.planner import ModelManager
from aurora.api import APIService
from aurora.governance.bundle import assemble_bundle
from aurora.governance.compliance import CompliancePolicy
from aurora.governance.compliance_checklist import checklist_summary, load_checklist
from aurora.governance.reports import (
    generate_governance_summary,
    generate_monthly_report,
    generate_training_report,
    generate_weekly_report,
)
from aurora.notify import NotificationService, load_notification_config


app = typer.Typer(help="AURORA-SE command-line interface")
eval_app = typer.Typer(help="Evaluation workflows")
session_app = typer.Typer(help="Session management")
plugin_app = typer.Typer(help="Plugin ecosystem")
workspace_app = typer.Typer(help="Workspace snapshot utilities")
telemetry_app = typer.Typer(help="Telemetry operations")
governance_app = typer.Typer(help="Governance utilities")
policy_app = typer.Typer(help="Policy engine controls")
scripts_app = typer.Typer(help="Automation scripts")
report_app = typer.Typer(help="Report generation")
model_app = typer.Typer(help="Model routing management")
notify_app = typer.Typer(help="Notification configuration")
api_app = typer.Typer(help="Local API server controls")

app.add_typer(eval_app, name="eval")
app.add_typer(session_app, name="session")
app.add_typer(plugin_app, name="plugin")
app.add_typer(workspace_app, name="workspace")
app.add_typer(telemetry_app, name="telemetry")
app.add_typer(governance_app, name="governance")
app.add_typer(policy_app, name="policy")
app.add_typer(scripts_app, name="scripts")
app.add_typer(report_app, name="report")
app.add_typer(model_app, name="model")
app.add_typer(notify_app, name="notify")
app.add_typer(api_app, name="api")


@app.callback(invoke_without_command=True)
def root(ctx: typer.Context, version: bool = typer.Option(False, "--version", is_eager=True)) -> None:
    """Root command dispatch handling global options."""
    if version:
        typer.echo(f"aurora-se {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def init() -> None:
    """Bootstrap configuration for the current repository."""
    typer.echo("Initializing AURORA-SE workspace (placeholder)")


@app.command()
def index(
    full: bool = typer.Option(False, "--full"),
    incremental: bool = typer.Option(False, "--incremental"),
    root: Path = typer.Option(Path.cwd(), "--root", exists=True, file_okay=False, dir_okay=True),
    config_path: Path = typer.Option(Path("configs/indexer.yaml"), "--config", exists=True),
) -> None:
    """Run the repository indexer."""
    job = IndexJobConfig(root=root, full=full, incremental=incremental)
    config = load_indexer_config(Path.cwd(), config_path)
    parser = TreeSitterParser(config)
    graph_store = GraphStore(config.database_url)
    embedding_store = EmbeddingStore(enabled=config.embeddings_enabled, model=config.embedding_model)
    service = IndexerService(config=config, graph_store=graph_store, parser=parser, embedding_store=embedding_store)
    service.run(job)
    typer.echo("Indexing complete")


@app.command()
def plan(
    task: str = typer.Option(..., "--task"),
    auto: bool = typer.Option(False, "--auto"),
    critic: bool = typer.Option(False, "--critic"),
    config_path: Path = typer.Option(Path("configs/model.yaml"), "--config", exists=True),
    output_format: str = typer.Option(
        "text",
        "--format",
        help="Output format for plan results (text, json, markdown).",
        case_sensitive=False,
    ),
    show_telemetry: bool = typer.Option(
        False,
        "--show-telemetry/--no-telemetry",
        help="Display timing and token estimates after planning.",
    ),
) -> None:
    """Generate a self-edit plan for the specified task."""

    planner_service = PlannerService(
        config_path=config_path,
        graph_store=GraphStore("sqlite:///artifacts/index.db"),
        embedding_store=EmbeddingStore(enabled=True, database_url="sqlite:///artifacts/index.db"),
        experience_vault=None,
    )

    plan_path = Path("artifacts/self_edit.json")
    start = time.perf_counter()

    async def _run() -> None:
        await planner_service.generate_self_edit(task=task, auto=auto, critic=critic)

    asyncio.run(_run())
    duration = time.perf_counter() - start
    telemetry = {
        "duration_seconds": round(duration, 3),
        "token_estimate": 320,
        "cost_estimate": round(duration * 0.001, 4),
    }
    _render_plan_output(plan_path, output_format.lower(), telemetry if show_telemetry else None)


@app.command()
def reward(
    compute: bool = typer.Option(False, "--compute/--no-compute", help="Compute reward from CI results."),
    explain: bool = typer.Option(False, "--explain/--no-explain", help="Render latest explainability artifact."),
    config: Path = typer.Option(Path("configs/reward.yaml"), "--config", exists=True),
    ci_results: Path | None = typer.Option(
        None,
        "--ci-results",
        exists=True,
        help="Path to CI results JSON (list of step dicts).",
    ),
) -> None:
    """Manual reward engine operations."""

    service = RewardService.from_config(config)
    result: RewardResult | None = None
    if compute:
        payload: list[dict[str, Any]]
        if ci_results:
            payload = json.loads(ci_results.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                raise typer.BadParameter("CI results must be a list of dictionaries.")
        else:
            payload = [{"step": "manual", "success": True}]
        result = service.evaluate(payload)
        _render_reward_result(result)
    if explain:
        path = service.render_explainability()
        typer.echo(f"Explainability artifact available at {path}")
    if not compute and not explain:
        typer.echo("No action selected. Use --compute and/or --explain.")

@app.command()
def apply(
    edit: Path = typer.Option(Path("artifacts/self_edit.json"), "--edit", exists=True),
    profile: str = typer.Option("fast", "--profile"),
    executor_config: Path = typer.Option(Path("configs/ci_profiles.yaml"), "--ci-config", exists=True),
) -> None:
    """Apply a self-edit inside sandbox and run CI profile."""

    config = load_executor_config(Path.cwd(), executor_config)
    error_logger = ErrorLogger(Path("telemetry/errors.jsonl"))
    sandbox: SandboxRunner
    policies = config.sandbox_policies
    if config.sandbox == "docker" and config.docker:
        mounts = build_mounts(config.docker.mounts)
        network = config.docker.network
        if policies and not policies.egress_allowed:
            network = "none"
        sandbox = DockerSandbox(
            image=config.docker.image,
            mounts=mounts,
            env=config.docker.env,
            network=network,
            seccomp_profile=config.docker.seccomp_profile,
            apparmor_profile=config.docker.apparmor_profile,
            cpu_limit=config.docker.cpu_limit,
            memory_limit=config.docker.memory_limit,
            read_only_root=config.docker.read_only_root,
            additional_args=config.docker.additional_args or (),
        )
    elif config.sandbox == "firecracker" and config.firecracker_config:
        resources_cfg = config.firecracker_config.resources or {}
        resources = FirecrackerResources(
            vcpu_count=resources_cfg.get("vcpu_count", 2),
            memory_mib=resources_cfg.get("memory_mib", 1024),
            jailer_user=resources_cfg.get("jailer_user", 1000),
            jailer_group=resources_cfg.get("jailer_group", 1000),
        )
        network_cfg = config.firecracker_config.network
        firecracker_network = None
        if network_cfg and policies and policies.egress_allowed:
            firecracker_network = FirecrackerNetwork(
                tap_device=network_cfg["tap_device"],
                mac_address=network_cfg.get("mac_address", "AA:FC:00:00:00:01"),
            )
        sandbox = FirecrackerSandbox(
            kernel_image=config.firecracker_config.kernel_image,
            rootfs_image=config.firecracker_config.rootfs_image,
            workspace=config.workspace,
            resources=resources,
            network=firecracker_network,
            egress_allowed=bool(policies and policies.egress_allowed),
            firecracker_bin=config.firecracker_config.firecracker_bin,
            firectl_bin=config.firecracker_config.firectl_bin,
            snapshot_dir=config.firecracker_config.snapshot_dir,
            error_logger=error_logger,
        )
    else:
        sandbox = LocalSandbox()
    ci_orchestrator = CIOrchestrator(sandbox=sandbox, artifacts_dir=Path("artifacts"))
    secret_config = load_secret_scanner_config(Path("policies/secrets.yaml"), error_logger=error_logger)
    secret_scanner = SecretScanner(secret_config)
    policy_evaluator = PolicyEvaluator(config.policy_path)
    executor = ExecutorService(
        config=config,
        ci_orchestrator=ci_orchestrator,
        secret_scanner=secret_scanner,
        policy_evaluator=policy_evaluator,
    )
    executor.apply(edit_path=edit, profile=profile)
    typer.echo("Executor run completed")


@app.command()
def shell(
    script: str | None = typer.Option(None, "--script", help="Semicolon-separated commands for non-interactive mode"),
) -> None:
    """Launch the interactive Aurora-SE shell."""

    session_manager = SessionManager()
    autopilot_service = AutopilotService(
        AutopilotConfig(
            session_root=Path("artifacts/sessions"),
            plan_config=Path("configs/model.yaml"),
            executor_config=Path("configs/ci_profiles.yaml"),
            reward_config=Path("configs/reward.yaml"),
            evaluation_config=Path("configs/eval.yaml"),
            plugins=(),
        ),
        session_manager=session_manager,
    )
    reward_service = RewardService.from_config(Path("configs/reward.yaml"))
    policy_evaluator = PolicyEvaluator(Path("policies/security.yaml"))
    shell_session = ShellSession(
        session_manager=session_manager,
        autopilot_service=autopilot_service,
        model_manager=ModelManager(Path("configs/model.yaml")),
        workspace_manager=WorkspaceManager(),
        extension_registry=ExtensionRegistry(),
        reward_service=reward_service,
        policy_evaluator=policy_evaluator,
        telemetry_log=Path("telemetry/errors.jsonl"),
        extensions_config=Path("configs/extensions.txt"),
    )
    if script:
        commands = [part.strip() for part in script.split(";") if part.strip()]

        def _emit(line: str) -> None:
            typer.echo(line)

        shell_session.run(commands, output=_emit)
    else:
        shell_session.run()


@app.command()
def learn(
    mode: str = typer.Option(
        "batch",
        "--mode",
        help="Run mode: batch executes once, interactive prompts for confirmations, nightly honours scheduler hooks.",
    ),
    config_path: Path = typer.Option(Path("configs/learn.yaml"), "--config", exists=True),
    federated: bool = typer.Option(False, "--federated/--no-federated", help="Sync adapters to federation after training."),
) -> None:
    """Run adapter learning pipeline."""

    normalized_mode = mode.lower()
    if normalized_mode not in {"batch", "interactive", "nightly"}:
        raise typer.BadParameter("Mode must be one of: batch, interactive, nightly")
    config = load_training_config(Path.cwd(), config_path)
    service = LearningService(config)
    nightly = normalized_mode == "nightly"
    interactive = normalized_mode == "interactive"
    service.run(nightly=nightly, federated=federated, interactive=interactive)

    metadata_path = config.output_adapter / "metadata.json"
    typer.echo(f"Adapter trained: {config.domain}:{config.adapter_version}")
    typer.echo(f"Metadata available at {metadata_path}")

    if nightly and config.scheduler.nightly_cron:
        typer.echo(f"Nightly schedule: {config.scheduler.nightly_cron}")

    if federated and config.federation_config:
        federation_cfg = FederationConfig.from_yaml(config.federation_config)
        typer.echo(f"Federation audit log: {federation_cfg.audit_log_path}")

    if interactive:
        typer.echo("Interactive mode complete; review metadata before publishing.")


@app.command()
def autopilot(
    task: str = typer.Option(..., "--task", help="Task description to execute."),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Skip evaluation and executor side effects."),
    require_confirm: bool = typer.Option(False, "--require-confirm/--no-confirm", help="Prompt before applying changes."),
    plan_config: Path = typer.Option(Path("configs/model.yaml"), "--plan-config", exists=True),
    executor_config: Path = typer.Option(Path("configs/ci_profiles.yaml"), "--executor-config", exists=True),
    reward_config: Path = typer.Option(Path("configs/reward.yaml"), "--reward-config", exists=True),
    evaluation_config: Path = typer.Option(Path("configs/eval.yaml"), "--evaluation-config", exists=True),
    session_root: Path = typer.Option(Path("artifacts/sessions"), "--session-root"),
    plugin: list[str] = typer.Option([], "--plugin", help="Extension spec module:Class", show_default=False),
    output_format: str = typer.Option("text", "--format", case_sensitive=False, help="Output format: text, json, markdown."),
    max_iterations: int | None = typer.Option(
        None,
        "--max-iterations",
        min=1,
        help="Maximum number of PDCA cycles before stopping.",
    ),
    max_cost: float | None = typer.Option(
        None,
        "--max-cost",
        min=0.0,
        help="Abort autopilot if estimated token cost exceeds this USD value.",
    ),
    seed: int | None = typer.Option(None, "--seed", help="Seed for deterministic autopilot heuristics."),
) -> None:
    """Run the autopilot loop (plan -> apply -> reward -> eval)."""

    config = AutopilotConfig(
        session_root=session_root,
        plan_config=plan_config,
        executor_config=executor_config,
        reward_config=reward_config,
        evaluation_config=evaluation_config,
        plugins=tuple(plugin),
    )
    service = AutopilotService(config)

    def _confirm() -> bool:
        return typer.confirm("Continue to apply changes?")

    report = service.run(
        task=task,
        dry_run=dry_run,
        require_confirm=require_confirm,
        confirm_callback=_confirm if require_confirm else None,
        max_iterations=max_iterations,
        max_cost=max_cost,
        seed=seed,
    )
    _render_autopilot_report(report, output_format.lower())


@session_app.command("start")
def session_start(
    name: str = typer.Argument(...),
    description: str = typer.Option("", "--description"),
    metadata: str | None = typer.Option(None, "--metadata", help="Additional metadata as JSON."),
) -> None:
    """Create a new workspace session."""

    manager = SessionManager()
    extra = json.loads(metadata) if metadata else {}
    session = manager.start(name=name, description=description, metadata=extra)
    typer.echo(json.dumps(session.metadata, indent=2))


@session_app.command("resume")
def session_resume(session_id: str = typer.Argument(...)) -> None:
    """Resume a previously created session."""

    manager = SessionManager()
    session = manager.resume(session_id)
    typer.echo(json.dumps(session.metadata, indent=2))


@session_app.command("archive")
def session_archive(
    session_id: str = typer.Argument(...),
    reason: str | None = typer.Option(None, "--reason"),
) -> None:
    """Archive an existing session."""

    manager = SessionManager()
    session = manager.archive(session_id, reason)
    typer.echo(json.dumps(session.metadata, indent=2))


@session_app.command("list")
def session_list(
    output_format: str = typer.Option("table", "--format", case_sensitive=False, help="table or json"),
) -> None:
    """List known sessions."""

    manager = SessionManager()
    sessions = list(manager.list())
    if output_format.lower() == "json":
        payload = [s.metadata for s in sessions]
        typer.echo(json.dumps(payload, indent=2))
        return
    if not sessions:
        typer.echo("No sessions found.")
        return
    typer.echo("Session ID  Status     Name")
    for session in sessions:
        typer.echo(f"{session.id:<10} {session.status:<9} {session.name}")


@session_app.command("delete")
def session_delete(session_id: str = typer.Argument(..., help="Session identifier to delete.")) -> None:
    """Delete a session and its artifacts."""

    manager = SessionManager()
    session = manager.resume(session_id)
    shutil.rmtree(session.path, ignore_errors=True)
    typer.echo(f"Session {session_id} deleted.")


@plugin_app.command("list")
def plugin_list(
    config: Path = typer.Option(Path("configs/extensions.txt"), "--config", help="Extensions config file."),
) -> None:
    """List registered plugins and registry metadata."""

    specs = _read_extension_specs(config)
    registry = ExtensionRegistry()
    if not specs and not registry.list():
        typer.echo("No plugins registered.")
        return
    if specs:
        typer.echo("Config entries:")
        for spec in specs:
            typer.echo(f"- {spec}")
    entries = registry.list()
    if entries:
        typer.echo("Registry entries:")
        for manifest in entries:
            typer.echo(f"- {manifest.name} ({manifest.version}) -> {manifest.spec}")


@plugin_app.command("create")
def plugin_create(
    name: str = typer.Argument(..., help="Human-friendly plugin name."),
    directory: Path = typer.Option(Path("extensions"), "--directory", file_okay=False, dir_okay=True),
) -> None:
    """Create a plugin scaffold."""

    directory.mkdir(parents=True, exist_ok=True)
    module_path = directory / f"{name.lower().replace(' ', '_')}_plugin.py"
    if module_path.exists():
        raise typer.BadParameter(f"Plugin module {module_path} already exists.")
    module_path.write_text(
        "from aurora.extensions.base import AuroraExtension\n\n"
        f"class {name.replace(' ', '')}Plugin(AuroraExtension):\n"
        "    def on_autopilot_start(self) -> None:\n"
        "        print('Plugin activated')\n",
        encoding="utf-8",
    )
    typer.echo(f"Plugin scaffold created at {module_path}")


@plugin_app.command("install")
def plugin_install(
    name: str = typer.Argument(...),
    spec: str = typer.Option(..., "--spec", help="Module:Class spec to load."),
    source: Path = typer.Option(Path("."), "--source", help="Directory containing the plugin code."),
    config: Path = typer.Option(Path("configs/extensions.txt"), "--config"),
) -> None:
    """Install a plugin into the registry and config file."""

    registry = ExtensionRegistry()
    manifest = registry.add(name=name, spec=spec, source_path=source.resolve())
    specs = set(_read_extension_specs(config))
    specs.add(spec)
    _write_extension_specs(config, sorted(specs))
    typer.echo(f"Installed plugin {manifest.name} ({manifest.version}) with signature {manifest.signature}")


@plugin_app.command("remove")
def plugin_remove(
    name: str = typer.Argument(...),
    config: Path = typer.Option(Path("configs/extensions.txt"), "--config"),
) -> None:
    """Remove a plugin from registry and config."""

    registry = ExtensionRegistry()
    manifest = registry.get(name)
    if not manifest:
        typer.echo(f"Plugin {name} not found in registry.")
    registry.remove(name)
    if manifest:
        specs = [spec for spec in _read_extension_specs(config) if spec != manifest.spec]
        _write_extension_specs(config, specs)
    typer.echo(f"Removed plugin {name}.")


@plugin_app.command("sign")
def plugin_sign(
    name: str = typer.Argument(...),
) -> None:
    """Display plugin signature."""

    registry = ExtensionRegistry()
    manifest = registry.get(name)
    if not manifest:
        raise typer.BadParameter(f"Plugin {name} not found.")
    typer.echo(f"{name} signature: {manifest.signature}")


@plugin_app.command("publish")
def plugin_publish(
    name: str = typer.Argument(...),
    destination: Path = typer.Option(Path("artifacts/extensions"), "--destination", file_okay=False, dir_okay=True),
) -> None:
    """Publish plugin metadata to the marketplace directory."""

    registry = ExtensionRegistry()
    manifest = registry.get(name)
    if not manifest:
        raise typer.BadParameter(f"Plugin {name} not registered.")
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / f"{name}.json"
    manifest_path.write_text(
        json.dumps(
            {
                "name": manifest.name,
                "spec": manifest.spec,
                "version": manifest.version,
                "signature": manifest.signature,
                "path": str(manifest.path),
                "published_at": datetime.now().isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    typer.echo(f"Published plugin manifest to {manifest_path}")


@plugin_app.command("validate")
def plugin_validate(spec: str = typer.Argument(..., help="Extension spec module:Class")) -> None:
    """Load a single extension spec to ensure it is valid."""

    manager = ExtensionManager()
    manager.load_many([spec])
    typer.echo(f"Loaded {len(manager.extensions)} extension(s).")


@workspace_app.command("snapshot")
def workspace_snapshot(
    tag: str | None = typer.Option(None, "--tag", help="Snapshot tag name."),
    path: list[Path] = typer.Option([], "--path", help="Specific paths to include."),
) -> None:
    """Create a workspace snapshot archive."""

    manager = WorkspaceManager()
    include = path or None
    snapshot = manager.snapshot(tag=tag, include=include)
    typer.echo(
        f"Snapshot '{snapshot.tag}' created at {snapshot.archive_path} ({snapshot.size_bytes} bytes) on {snapshot.created_at}"
    )


@workspace_app.command("restore")
def workspace_restore(
    tag: str = typer.Argument(..., help="Snapshot tag to restore."),
    destination: Path = typer.Option(Path.cwd(), "--destination", file_okay=False, dir_okay=True),
) -> None:
    """Restore a snapshot into the destination directory."""

    manager = WorkspaceManager()
    manager.restore(tag=tag, destination=destination)
    typer.echo(f"Restored snapshot '{tag}' into {destination}")


@workspace_app.command("status")
def workspace_status() -> None:
    """Display snapshot inventory."""

    manager = WorkspaceManager()
    info = manager.status()
    typer.echo(json.dumps(info, indent=2))


@telemetry_app.command("init")
def telemetry_init(
    environment: str = typer.Option("local", "--environment", "-e", help="Telemetry environment profile."),
    config: Path | None = typer.Option(None, "--config", exists=True, help="Override telemetry config."),
) -> None:
    """Initialize telemetry pipelines."""

    resolved_config = _resolve_telemetry_config(config, environment)
    service = TelemetryService.from_config(resolved_config)
    typer.echo(
        f"Telemetry initialized for {service.config.environment} "
        f"(service {service.config.service_name}, collector={service.config.collector_config})"
    )


@telemetry_app.command("dashboard")
def telemetry_dashboard(
    environment: str = typer.Option("local", "--environment", "-e", help="Telemetry environment profile."),
    config: Path | None = typer.Option(None, "--config", exists=True, help="Override telemetry config."),
    export: bool = typer.Option(False, "--export/--no-export", help="Export dashboard metadata."),
    remote: bool = typer.Option(False, "--remote/--local", help="Show remote Grafana dashboard link."),
    output: Path = typer.Option(Path("artifacts/telemetry/dashboard.json"), "--output"),
) -> None:
    """Display telemetry dashboard location and optionally export metadata."""

    resolved_config = _resolve_telemetry_config(config, environment)
    service = TelemetryService.from_config(resolved_config)
    links = service.dashboard_links()
    target = links["grafana"] if remote else links["service"]
    typer.echo(f"Dashboard available at {target}")
    if export:
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "service": service.config.service_name,
            "environment": service.config.environment,
            "dashboard_local": links["service"],
            "dashboard_grafana": links["grafana"],
            "collector_config": str(service.config.collector_config) if service.config.collector_config else None,
            "prometheus": {
                "port": service.config.prometheus_port,
                "targets": service.config.prometheus_targets,
                "scrape_interval": service.config.prometheus_scrape_interval,
            },
            "log_retention_days": service.config.log_retention_days,
            "log_aggregation": {
                "provider": service.config.log_aggregation_provider,
                "bucket": service.config.log_aggregation_bucket,
            },
            "alerting": service.alerting_metadata(),
            "exported_at": datetime.now().isoformat(),
        }
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        typer.echo(f"Dashboard metadata exported to {output}")


@telemetry_app.command("export")
def telemetry_export(
    source: Path = typer.Option(Path("telemetry/errors.jsonl"), "--source"),
    destination: Path = typer.Option(Path("artifacts/telemetry/export.jsonl"), "--destination"),
    interval: str | None = typer.Option(None, "--interval", help="Time range to annotate (e.g. 1h, 24h)."),
    environment: str = typer.Option("local", "--environment", "-e", help="Telemetry environment profile."),
) -> None:
    """Export telemetry logs to a destination path."""

    if not source.exists():
        raise typer.BadParameter(f"Telemetry source {source} not found.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(source, destination)
    typer.echo(f"Telemetry logs exported to {destination}")
    if interval:
        line_count = sum(1 for _ in destination.open("r", encoding="utf-8"))
        meta_payload = {
            "interval": interval,
            "environment": environment,
            "source": str(source),
            "destination": str(destination),
            "exported_at": datetime.now().isoformat(),
            "lines": line_count,
        }
        meta_path = destination.with_suffix(destination.suffix + ".meta.json")
        meta_path.write_text(json.dumps(meta_payload, indent=2), encoding="utf-8")
        typer.echo(f"Export metadata written to {meta_path}")


@governance_app.command("bundle")
def governance_bundle(
    evaluation: Path = typer.Option(Path("docs/governance/bundles/lite_latest.json"), "--evaluation", exists=True),
    output: Path = typer.Option(Path("docs/governance/bundles/current_bundle.json"), "--output"),
    overrides: Path | None = typer.Option(None, "--overrides", exists=True),
    sbom: Path | None = typer.Option(None, "--sbom", exists=True, help="SBOM artifact to embed."),
    cve_report: Path | None = typer.Option(None, "--cve-report", exists=True, help="CVE report JSON."),
    alert_rules: Path | None = typer.Option(
        Path("configs/alerting/prometheus_rules.yaml"),
        "--alert-rules",
        exists=True,
        help="Prometheus alert rules to include.",
    ),
) -> None:
    """Assemble a governance bundle from the latest evaluation artifacts."""

    evaluation_report = json.loads(evaluation.read_text(encoding="utf-8"))
    overrides_payload = []
    if overrides:
        overrides_payload = json.loads(overrides.read_text(encoding="utf-8"))
    bundle = assemble_bundle(
        output,
        evaluation_report,
        overrides_payload,
        sbom_path=sbom,
        cve_path=cve_report,
        alert_rules_path=alert_rules,
    )
    typer.echo(f"Governance bundle written to {bundle.output_path}")


@governance_app.command("policy")
def governance_policy(
    report: Path = typer.Argument(..., exists=True, help="Evaluation report JSON to validate."),
    max_bias: float = typer.Option(0.05, "--max-bias"),
    require_sbom: bool = typer.Option(True, "--require-sbom/--no-require-sbom"),
) -> None:
    """Evaluate governance report against compliance policy."""

    policy = CompliancePolicy(max_bias_score=max_bias, require_sbom=require_sbom)
    payload = json.loads(report.read_text(encoding="utf-8"))
    evaluation = payload.get("evaluation", payload)
    if isinstance(evaluation, dict) and "sbom" not in evaluation and "evaluation" in evaluation:
        evaluation = evaluation.get("evaluation", evaluation)
    issues = policy.evaluate(evaluation)
    if issues:
        typer.echo("Policy issues detected:")
        for issue in issues:
            typer.echo(f"- {issue}")
        raise typer.Exit(code=1)
    typer.echo("Report complies with policy requirements.")


@governance_app.command("report")
def governance_report(
    weekly: bool = typer.Option(False, "--weekly", help="Generate weekly governance report."),
    monthly: bool = typer.Option(False, "--monthly", help="Generate monthly governance overview."),
    metrics_csv: Path = typer.Option(Path("artifacts/eval/metrics.csv"), "--metrics", help="Metrics CSV path."),
    dashboard_html: Path = typer.Option(
        Path("artifacts/eval/dashboard.html"), "--dashboard", help="Dashboard HTML path."
    ),
    incidents_csv: Path = typer.Option(
        Path("artifacts/eval/incidents.csv"), "--incidents", help="Incident log for monthly summaries."
    ),
) -> None:
    """Generate governance reports and summaries."""

    if weekly and monthly:
        raise typer.BadParameter("Specify only one of --weekly or --monthly.")
    if monthly:
        report = generate_monthly_report(metrics_csv=metrics_csv, incidents_csv=incidents_csv)
        typer.echo(f"Monthly report generated at {report.output_path}")
        return
    report = generate_weekly_report(metrics_csv=metrics_csv, dashboard_html=dashboard_html)
    typer.echo(f"Weekly report generated at {report.output_path}")


@governance_app.command("compliance")
def governance_compliance(
    checklist: Path = typer.Option(Path("configs/compliance/soc2_checklist.yaml"), "--checklist", exists=True),
) -> None:
    """Run compliance checklist automation and output summary."""

    data = load_checklist(checklist)
    summary = checklist_summary(data)
    payload = data.as_dict()
    payload["summary"] = summary
    typer.echo(json.dumps(payload, indent=2))


@policy_app.command("list")
def policy_list(
    config: Path = typer.Option(Path("configs/policy_profiles.yaml"), "--config"),
) -> None:
    """List available policy profiles."""

    profiles = _load_policy_profiles(config)
    if not profiles:
        typer.echo("No policy profiles defined.")
        return
    typer.echo("Available policy profiles:")
    for name, payload in profiles.items():
        description = payload.get("description", "")
        typer.echo(f"- {name}: {description}")


@policy_app.command("set")
def policy_set(
    profile: str = typer.Argument(...),
    config: Path = typer.Option(Path("configs/policy_profiles.yaml"), "--config"),
    active_path: Path = typer.Option(Path("configs/policy_active.txt"), "--active-path"),
) -> None:
    """Set the active policy profile."""

    profiles = _load_policy_profiles(config)
    if profile not in profiles:
        raise typer.BadParameter(f"Profile '{profile}' not found in {config}.")
    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_text(profile, encoding="utf-8")
    typer.echo(f"Active policy profile set to {profile}")


@policy_app.command("check")
def policy_check(
    profile: str | None = typer.Option(None, "--profile", help="Profile name; defaults to active."),
    config: Path = typer.Option(Path("configs/policy_profiles.yaml"), "--config"),
    results: Path | None = typer.Option(None, "--results", exists=True, help="CI results JSON path."),
) -> None:
    """Validate CI results against the configured policy."""

    profiles = _load_policy_profiles(config)
    if not profiles:
        raise typer.BadParameter("No policy profiles configured.")
    active_profile = profile or _load_active_policy(Path("configs/policy_active.txt"))
    if active_profile not in profiles:
        raise typer.BadParameter(f"Profile '{active_profile}' not found in {config}.")
    policy_path = Path(profiles[active_profile]["path"])
    evaluator = PolicyEvaluator(policy_path)
    required_steps = profiles[active_profile].get("required_steps")
    payload: list[dict[str, Any]]
    if results:
        payload = json.loads(results.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise typer.BadParameter("Results file must contain a list of step dictionaries.")
    else:
        policy_data = yaml.safe_load(Path(profiles[active_profile]["path"]).read_text(encoding="utf-8"))
        required = policy_data.get("ci", {}).get("required_steps", [])
        payload = [{"step": step, "success": True} for step in required]
    metadata = {
        "sbom": "artifacts/sbom/latest.json",
        "cve_report": {"summary": {"critical": 0, "high": 0}},
        "license_report": {"packages": [{"name": "aurora", "license": "MIT"}]},
    }
    outcome = evaluator.evaluate(payload, metadata=metadata)
    typer.echo(json.dumps({"accepted": outcome.accepted, "reasons": outcome.reasons}, indent=2))


@report_app.command("weekly")
def report_weekly(
    metrics_csv: Path = typer.Option(Path("artifacts/eval/metrics.csv"), "--metrics"),
    dashboard_html: Path = typer.Option(Path("artifacts/eval/dashboard.html"), "--dashboard"),
) -> None:
    """Generate the weekly governance report."""

    report = generate_weekly_report(metrics_csv, dashboard_html)
    typer.echo(f"Weekly report generated at {report.output_path}")


@report_app.command("monthly")
def report_monthly(
    metrics_csv: Path = typer.Option(Path("artifacts/eval/monthly_metrics.csv"), "--metrics"),
    incidents_csv: Path = typer.Option(Path("artifacts/eval/incidents.csv"), "--incidents"),
) -> None:
    """Generate the monthly governance overview."""

    report = generate_monthly_report(metrics_csv, incidents_csv)
    typer.echo(f"Monthly report generated at {report.output_path}")


@report_app.command("governance")
def report_governance(
    bundle_path: Path = typer.Option(Path("docs/governance/bundles/current_bundle.json"), "--bundle", exists=True),
) -> None:
    """Generate a summary for the latest governance bundle."""

    report = generate_governance_summary(bundle_path)
    typer.echo(f"Governance summary written to {report.output_path}")


@report_app.command("training")
def report_training(
    training_log: Path = typer.Option(Path("artifacts/training/log.jsonl"), "--log"),
    adapters_path: Path = typer.Option(Path("adapters"), "--adapters"),
) -> None:
    """Generate a training status report."""

    report = generate_training_report(training_log, adapters_path)
    typer.echo(f"Training report available at {report.output_path}")


@model_app.command("list")
def model_list(config: Path = typer.Option(Path("configs/model.yaml"), "--config", exists=True)) -> None:
    """List available model routing profiles."""

    manager = ModelManager(config)
    profiles = manager.list_profiles()
    if not profiles:
        typer.echo("No model routes defined.")
        return
    typer.echo("Available model routes:")
    for profile in profiles:
        prefix = "*" if profile.name == manager.default_profile() else " "
        typer.echo(f"{prefix} {profile.name} -> {profile.provider}:{profile.model}")


@model_app.command("switch")
def model_switch(
    profile: str = typer.Argument(...),
    config: Path = typer.Option(Path("configs/model.yaml"), "--config", exists=True),
) -> None:
    """Switch default model routing profile."""

    manager = ModelManager(config)
    manager.switch(profile)
    typer.echo(f"Default model profile set to {profile}")


@model_app.command("test")
def model_test(
    profile: str = typer.Argument(...),
    config: Path = typer.Option(Path("configs/model.yaml"), "--config", exists=True),
) -> None:
    """Show profile configuration for validation."""

    manager = ModelManager(config)
    payload = manager.test(profile)
    typer.echo(json.dumps(payload, indent=2))


@notify_app.command("slack")
def notify_slack(
    message: str = typer.Argument(..., help="Message to send."),
    config: Path = typer.Option(Path("configs/notify.yaml"), "--config", exists=True),
) -> None:
    """Send a Slack notification using configured webhook."""

    service = NotificationService(load_notification_config(config))
    log_path = service.send("slack", message, metadata={"type": "slack"})
    typer.echo(f"Slack notification logged to {log_path}")


@notify_app.command("email")
def notify_email(
    subject: str = typer.Option("Aurora-SE Notification", "--subject"),
    body: str = typer.Argument(...),
    config: Path = typer.Option(Path("configs/notify.yaml"), "--config", exists=True),
) -> None:
    """Send an email notification (logged to audit trail)."""

    service = NotificationService(load_notification_config(config))
    log_path = service.send("email", body, metadata={"subject": subject})
    typer.echo(f"Email notification logged to {log_path}")


@notify_app.command("webhook")
def notify_webhook(
    event: str = typer.Argument(..., help="Event identifier."),
    payload: Path | None = typer.Option(None, "--payload", exists=True, help="JSON payload file."),
    config: Path = typer.Option(Path("configs/notify.yaml"), "--config", exists=True),
) -> None:
    """Send a webhook notification."""

    metadata = {"event": event}
    if payload:
        metadata["payload"] = json.loads(payload.read_text(encoding="utf-8"))
    service = NotificationService(load_notification_config(config))
    log_path = service.send("webhook", f"Webhook event {event}", metadata=metadata)
    typer.echo(f"Webhook notification logged to {log_path}")


@api_app.command("start")
def api_start(
    port: int = typer.Option(8080, "--port", min=1024, max=65535),
    state_path: Path = typer.Option(Path("artifacts/api/server.json"), "--state-path"),
) -> None:
    """Record API server start state."""

    service = APIService(state_path)
    state = service.start(port=port)
    typer.echo(json.dumps({"status": state.status, "port": state.port, "started_at": state.started_at}, indent=2))


@api_app.command("stop")
def api_stop(
    state_path: Path = typer.Option(Path("artifacts/api/server.json"), "--state-path"),
) -> None:
    """Record API server stop state."""

    service = APIService(state_path)
    state = service.stop()
    typer.echo(json.dumps({"status": state.status, "port": state.port, "started_at": state.started_at}, indent=2))


@api_app.command("status")
def api_status(
    state_path: Path = typer.Option(Path("artifacts/api/server.json"), "--state-path"),
) -> None:
    """Report API server status."""

    service = APIService(state_path)
    state = service.status()
    typer.echo(json.dumps({"status": state.status, "port": state.port, "started_at": state.started_at}, indent=2))


@scripts_app.command("run")
def scripts_run(
    script: str = typer.Argument(..., help="Script name relative to scripts/ directory."),
    args: list[str] = typer.Argument(None, help="Arguments to forward to the script."),
) -> None:
    """Execute automation script with forwarded arguments."""

    script_path = Path("scripts") / script if not Path(script).exists() else Path(script)
    if not script_path.exists():
        raise typer.BadParameter(f"Script {script} not found.")
    forwarded = list(args or [])
    if script_path.suffix == ".sh":
        command = ["bash", str(script_path), *forwarded]
    elif script_path.suffix == ".py":
        command = ["python", str(script_path), *forwarded]
    else:
        command = [str(script_path), *forwarded]
    result = subprocess.run(command, check=False)
    typer.echo(f"Script exited with code {result.returncode}")
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)


@eval_app.command("run")
def eval_run(
    suite: str = typer.Argument(..., help="Name of the evaluation suite to execute."),
    config_path: Path = typer.Option(Path("configs/eval.yaml"), "--config", exists=True),
) -> None:
    """Execute an evaluation suite and emit metrics."""

    config = load_evaluation_config(config_path)
    service = EvaluationService(config)
    result = service.run(suite)
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    typer.echo(json.dumps({"exit_code": result.exit_code, "metrics": metrics}, indent=2))
    typer.echo(f"Artifacts stored under {result.output_path.parent}")


@eval_app.command("compare")
def eval_compare(
    run_a: Path = typer.Argument(..., exists=True, help="Baseline metrics JSON"),
    run_b: Path = typer.Argument(..., exists=True, help="Comparison metrics JSON"),
) -> None:
    """Compare two evaluation runs and report metric deltas."""

    diff = compare_metrics(run_a, run_b)
    typer.echo(json.dumps(diff, indent=2))


@eval_app.command("report")
def eval_report(
    config_path: Path = typer.Option(Path("configs/eval.yaml"), "--config", exists=True),
    suite: str | None = typer.Option(None, "--suite", help="Filter results by suite"),
    limit: int = typer.Option(10, "--limit", min=1, help="Number of recent runs to display"),
    refresh_dashboard: bool = typer.Option(True, "--refresh-dashboard/--skip-dashboard"),
) -> None:
    """Summarize evaluation metrics and optionally regenerate the dashboard."""

    config = load_evaluation_config(config_path)
    df = load_metrics(config.results_dir)
    if df.empty:
        typer.echo("No evaluation metrics found.")
        return
    if suite is not None:
        df = df[df["suite"] == suite]
    summary = df.tail(limit)
    typer.echo(json.dumps(summary.to_dict(orient="records"), indent=2))
    if refresh_dashboard:
        generate_dashboard(config.results_dir, config.analytics.dashboard_html)
        typer.echo(f"Dashboard refreshed at {config.analytics.dashboard_html}")


@app.command()
def adapters(
    command: str = typer.Argument(..., metavar="COMMAND"),
    path: Path = typer.Option(Path("adapters"), "--path"),
    metadata: Path | None = typer.Option(None, "--metadata", help="Metadata JSON when using publish command."),
) -> None:
    """Adapter management commands."""

    if command == "list":
        adapters = list_adapters(path)
        typer.echo(json.dumps(adapters, indent=2))
    elif command == "sync":
        name = typer.prompt("Adapter name")
        version = typer.prompt("Adapter version")
        config_path = typer.prompt("Federation config", default="configs/federation.yaml")
        metadata_result = sync_adapter(path, name, version, Path(config_path))
        typer.echo(json.dumps(metadata_result, indent=2))
    elif command == "publish":
        meta_path = metadata or Path(typer.prompt("Metadata path", default=str(path / "metadata.json")))
        published = publish_adapter(path, meta_path)
        typer.echo(f"Published {published['name']}:{published['version']}")
    elif command == "rollback":
        name = typer.prompt("Adapter name")
        version = typer.prompt("Adapter version")
        resolved = rollback_adapter(path, name, version)
        typer.echo(f"Set active adapter to {resolved}")
    else:
        raise typer.BadParameter("Unsupported adapters command")

def _render_reward_result(result: RewardResult) -> None:
    payload = {
        "reward": result.reward,
        "success": result.success,
        "components": result.components,
        "penalties": result.penalties,
        "reasons": result.reasons,
    }
    typer.echo(json.dumps(payload, indent=2))


def _read_extension_specs(config: Path) -> list[str]:
    if not config.exists():
        return []
    entries: list[str] = []
    for line in config.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(line)
    return entries


def _write_extension_specs(config: Path, specs: Iterable[str]) -> None:
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("\n".join(specs) + ("\n" if specs else ""), encoding="utf-8")


def _resolve_telemetry_config(config: Path | None, environment: str | None) -> Path:
    if config is not None:
        return config
    env = (environment or "local").lower()
    candidate = Path("configs/telemetry") / f"{env}.yaml"
    if candidate.exists():
        return candidate
    fallback = Path("configs/telemetry.yaml")
    if fallback.exists():
        return fallback
    raise typer.BadParameter(f"No telemetry configuration found for environment '{env}'.")


def _load_policy_profiles(config: Path) -> dict[str, dict[str, Any]]:
    if not config.exists():
        return {}
    data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    return data.get("profiles", {})


def _load_active_policy(active_path: Path) -> str:
    if active_path.exists():
        return active_path.read_text(encoding="utf-8").strip()
    return "baseline"


def _render_plan_output(plan_path: Path, fmt: str, telemetry: dict[str, Any] | None) -> None:
    telemetry = telemetry or {}
    if fmt == "json":
        payload: dict[str, Any] = {"plan_path": str(plan_path)}
        if telemetry:
            payload["telemetry"] = telemetry
        typer.echo(json.dumps(payload, indent=2))
    elif fmt == "markdown":
        lines = ["# Plan Result", f"- plan path: `{plan_path}`"]
        if telemetry:
            lines.append("## Telemetry")
            lines.append(f"- duration: {telemetry.get('duration_seconds', 0)}s")
            lines.append(f"- tokens: {telemetry.get('token_estimate', 0)}")
            lines.append(f"- cost: ${telemetry.get('cost_estimate', 0)}")
        typer.echo("\n".join(lines))
    else:
        typer.echo(f"Self-edit plan saved to {plan_path}")
        if telemetry:
            typer.echo(
                "Telemetry: duration {dur}s | tokens~{tok} | cost~${cost}".format(
                    dur=telemetry.get("duration_seconds", 0),
                    tok=telemetry.get("token_estimate", 0),
                    cost=telemetry.get("cost_estimate", 0),
                )
            )


def _render_autopilot_report(report: AutopilotReport, fmt: str) -> None:
    payload = {
        "run_id": report.run_id,
        "task": report.task,
        "steps": list(report.steps),
        "duration_seconds": round(report.duration_seconds, 3),
        "estimated_tokens": report.estimated_tokens,
        "artifacts": {k: str(v) for k, v in report.artifacts.items()},
    }
    if fmt == "json":
        typer.echo(json.dumps(payload, indent=2))
        return
    if fmt == "markdown":
        lines = [
            f"# Autopilot Run {payload['run_id']}",
            f"- Task: {payload['task']}",
            f"- Duration: {payload['duration_seconds']}s",
            f"- Estimated tokens: {payload['estimated_tokens']}",
            "## Steps",
        ]
        lines.extend(f"- {step}" for step in report.steps)
        lines.append("## Artifacts")
        lines.extend(f"- {name}: `{path}`" for name, path in payload["artifacts"].items())
        typer.echo("\n".join(lines))
        return
    typer.echo(f"Autopilot run {payload['run_id']} completed in {payload['duration_seconds']}s")
    typer.echo("Steps:")
    for step in report.steps:
        typer.echo(f"- {step}")
    typer.echo("Artifacts:")
    for name, path in payload["artifacts"].items():
        typer.echo(f"- {name}: {path}")
    typer.echo(f"Estimated tokens: {report.estimated_tokens}")

def entrypoint() -> None:
    app()


def main() -> None:  # pragma: no cover - Typer CLI invocation
    entrypoint()


if __name__ == "__main__":  # pragma: no cover
    main()
