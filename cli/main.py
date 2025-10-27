"""Command-line interface for AURORA-SE."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from aurora import __version__
from aurora.indexer.config_loader import load_indexer_config
from aurora.indexer.store import GraphStore
from aurora.indexer.tree import TreeSitterParser
from aurora.indexer.embedding import EmbeddingStore
from aurora.indexer.service import IndexJobConfig, IndexerService
from aurora.planner.service import PlannerService
from aurora.planner.config_loader import load_planner_config
from aurora.executor.config_loader import load_executor_config
from aurora.executor import ExecutorService, CIOrchestrator, LocalSandbox
from aurora.security.secrets import SecretScanner, SecretScannerConfig
from aurora.learn.config import TrainingConfig, HardwareConfig
from aurora.learn.service import LearningService
from aurora.indexer.context import ContextPacker


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
        self_edit = await planner_service.generate_self_edit(task=task, auto=auto, critic=critic)
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
    sandbox = LocalSandbox()
    ci_orchestrator = CIOrchestrator(sandbox=sandbox, artifacts_dir=Path("artifacts"))
    secret_scanner = SecretScanner(SecretScannerConfig(patterns=(r"secret",)))
    executor = ExecutorService(config=config, ci_orchestrator=ci_orchestrator, secret_scanner=secret_scanner)
    executor.apply(edit_path=edit, profile=profile)
    typer.echo("Executor run completed")


@app.command()
def learn(
    nightly: bool = typer.Option(False, "--nightly"),
    gpu: str = typer.Option("auto", "--gpu"),
) -> None:
    """Run adapter learning pipeline."""

    config = TrainingConfig(
        adapters_path=Path("adapters"),
        data_path=Path("artifacts"),
        base_model="base-model",
        output_adapter=Path("adapters") / "default" / "latest",
        hardware=HardwareConfig(gpu_memory_gb=24, fallback_mode="cpu", precision="8bit"),
    )
    service = LearningService(config)
    service.run(nightly=nightly)
    typer.echo("Learning pipeline triggered")


def entrypoint() -> None:
    app()


def main() -> None:  # pragma: no cover - Typer CLI invocation
    entrypoint()


if __name__ == "__main__":  # pragma: no cover
    main()

