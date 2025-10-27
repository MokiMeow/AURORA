"""Command-line interface for AURORA-SE."""

from __future__ import annotations

import asyncio
from pathlib import Path
import json

import typer

from aurora import __version__
from aurora.indexer.config_loader import load_indexer_config
from aurora.indexer.store import GraphStore
from aurora.indexer.tree import TreeSitterParser
from aurora.indexer.embedding import EmbeddingStore
from aurora.indexer.service import IndexJobConfig, IndexerService
from aurora.planner.service import PlannerService
from aurora.executor.config_loader import load_executor_config
from aurora.executor import ExecutorService, CIOrchestrator, LocalSandbox
from aurora.executor.sandbox import DockerSandbox, FirecrackerSandbox, SandboxRunner
from aurora.security.secrets import SecretScanner, SecretScannerConfig
from aurora.executor.policy import PolicyEvaluator
from aurora.learn.config_loader import load_training_config
from aurora.learn.service import LearningService
from aurora.eval.config_loader import load_evaluation_config
from aurora.eval.service import EvaluationService
from aurora.learn.cli import list_adapters, sync_adapter, rollback_adapter
from aurora.telemetry.service import TelemetryService


app = typer.Typer(help="AURORA-SE command-line interface")


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
) -> None:
    """Generate a self-edit plan for the specified task."""

    planner_service = PlannerService(
        config_path=config_path,
        graph_store=GraphStore("sqlite:///artifacts/index.db"),
        embedding_store=EmbeddingStore(enabled=True, database_url="sqlite:///artifacts/index.db"),
        experience_vault=None,
    )

    async def _run() -> None:
        await planner_service.generate_self_edit(task=task, auto=auto, critic=critic)
        typer.echo("Self-edit plan saved to artifacts/self_edit.json")

    asyncio.run(_run())


@app.command()
def apply(
    edit: Path = typer.Option(Path("artifacts/self_edit.json"), "--edit", exists=True),
    profile: str = typer.Option("fast", "--profile"),
    executor_config: Path = typer.Option(Path("configs/ci_profiles.yaml"), "--ci-config", exists=True),
) -> None:
    """Apply a self-edit inside sandbox and run CI profile."""

    config = load_executor_config(Path.cwd(), executor_config)
    sandbox: SandboxRunner
    if config.sandbox == "docker":
        sandbox = DockerSandbox(
            image=config.docker_image or "aurora-se/executor:latest",
            mounts=config.docker_mounts or [],
            env=config.docker_env,
            network="none" if config.sandbox_policies and not config.sandbox_policies.egress_allowed else None,
        )
    elif config.sandbox == "firecracker" and config.firecracker_config:
        sandbox = FirecrackerSandbox(
            kernel_image=config.firecracker_config.kernel_image,
            rootfs_image=config.firecracker_config.rootfs_image,
            workspace=config.workspace,
        )
    else:
        sandbox = LocalSandbox()
    ci_orchestrator = CIOrchestrator(sandbox=sandbox, artifacts_dir=Path("artifacts"))
    secret_scanner = SecretScanner(SecretScannerConfig(patterns=(r"secret",)))
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
def learn(
    nightly: bool = typer.Option(False, "--nightly"),
    config_path: Path = typer.Option(Path("configs/learn.yaml"), "--config", exists=True),
    federated: bool = typer.Option(False, "--federated"),
) -> None:
    """Run adapter learning pipeline."""

    config = load_training_config(Path.cwd(), config_path)
    service = LearningService(config)
    service.run(nightly=nightly, federated=federated)
    typer.echo("Learning pipeline triggered")


@app.command()
def adapters(command: str = typer.Argument(...), path: Path = typer.Option(Path("adapters"), "--path")) -> None:
    """Adapter management commands."""

    if command == "list":
        adapters = list_adapters(path)
        typer.echo(json.dumps(adapters, indent=2))
    elif command == "sync":
        name = typer.prompt("Adapter name")
        version = typer.prompt("Adapter version")
        metadata = sync_adapter(path, name, version, Path("configs/federation.yaml"))
        typer.echo(json.dumps(metadata, indent=2))
    elif command == "rollback":
        name = typer.prompt("Adapter name")
        version = typer.prompt("Adapter version")
        resolved = rollback_adapter(path, name, version)
        typer.echo(f"Set active adapter to {resolved}")
    else:
        raise typer.BadParameter("Unsupported adapters command")


@app.command()
def eval(
    suite: str = typer.Option("swe-bench-lite", "--suite"),
    config_path: Path = typer.Option(Path("configs/eval.yaml"), "--config", exists=True),
    export_metrics: bool = typer.Option(True, "--export-metrics/--no-export-metrics"),
) -> None:
    """Run evaluation suite (SWE-Bench)."""

    config = load_evaluation_config(config_path)
    service = EvaluationService(config)
    result = service.run(suite_name=suite)
    typer.echo(
        "Evaluation completed with exit code "
        f"{result.exit_code}; results at {result.output_path}"
    )
    if export_metrics:
        typer.echo(f"Metrics saved to {result.metrics_path}")
        typer.echo(f"Compliance report saved to {result.compliance_path}")
        if result.sbom_path:
            typer.echo(f"SBOM snapshot at {result.sbom_path}")
        if result.telemetry_path:
            typer.echo(f"Telemetry snapshot at {result.telemetry_path}")


@app.command()
def telemetry(
    config_path: Path = typer.Option(Path("configs/telemetry.yaml"), "--config", exists=True),
    export: bool = typer.Option(False, "--export", help="Export PDCA log to stdout"),
) -> None:
    """Initialize telemetry stack or export PDCA log."""

    service = TelemetryService.from_config(config_path)
    if export:
        pdca_log = service.config.log_file
        if pdca_log.exists():
            typer.echo(pdca_log.read_text(encoding="utf-8"))
        else:
            typer.echo("PDCA log is empty")
    else:
        typer.echo("Telemetry stack initialized")


@app.command()
def governance(
    command: str = typer.Argument(..., metavar="COMMAND"),
    bundle_path: Path = typer.Option(Path("docs/governance/bundles/latest.json"), "--bundle"),
) -> None:
    """Governance utilities (bundle generation, policy checks)."""

    if command == "bundle":
        typer.echo(f"Latest governance bundle at {bundle_path}")
    elif command == "policy":
        typer.echo("Policy checks not yet implemented")
    else:
        raise typer.BadParameter("Unsupported governance command")


def entrypoint() -> None:
    app()


def main() -> None:  # pragma: no cover - Typer CLI invocation
    entrypoint()


if __name__ == "__main__":  # pragma: no cover
    main()

