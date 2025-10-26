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
from aurora.planner.service import PlannerConfig, PlannerService


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
    endpoint: str = typer.Option("http://localhost:11434/api/generate", "--endpoint"),
    model: str = typer.Option("deepseek-r1:7b", "--model"),
) -> None:
    """Generate a self-edit plan for the specified task."""

    config = PlannerConfig(endpoint=endpoint, model=model, critic_endpoints=[])
    service = PlannerService(config)

    async def _run() -> None:
        self_edit = await service.generate_self_edit(task=task, auto=auto, critic=critic)
        output_dir = Path("artifacts")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "self_edit.json"
        output_path.write_text(self_edit.model_dump_json(indent=2))
        typer.echo(f"Self-edit plan saved to {output_path}")

    asyncio.run(_run())


def entrypoint() -> None:
    app()


def main() -> None:  # pragma: no cover - Typer CLI invocation
    entrypoint()


if __name__ == "__main__":  # pragma: no cover
    main()

