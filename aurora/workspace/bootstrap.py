"""Create an AURORA workspace from bundled default resources."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

RESOURCE_TREES = ("configs", "policies", "prompts", "queries", "scripts")
RUNTIME_DIRECTORIES = ("artifacts", "telemetry", "experience")


@dataclass(frozen=True)
class BootstrapResult:
    """Counts reported after copying default resource files."""

    created: int
    skipped: int


def bootstrap_workspace(root: Path) -> BootstrapResult:
    """Create runtime directories and copy missing defaults beneath ``root``."""

    resolved_root = root.resolve()
    resolved_root.mkdir(parents=True, exist_ok=True)
    for relative_path in RUNTIME_DIRECTORIES:
        (resolved_root / relative_path).mkdir(parents=True, exist_ok=True)

    resource_root = _resource_root()
    created = 0
    skipped = 0
    for tree_name in RESOURCE_TREES:
        source_tree = resource_root.joinpath(tree_name)
        if not source_tree.is_dir():
            raise FileNotFoundError(f"AURORA resource tree is missing: {tree_name}")
        tree_created, tree_skipped = _copy_missing(source_tree, resolved_root / tree_name, resolved_root)
        created += tree_created
        skipped += tree_skipped
    return BootstrapResult(created=created, skipped=skipped)


def _resource_root() -> Any:
    packaged_root = resources.files("aurora").joinpath("resources")
    if packaged_root.is_dir():
        return packaged_root

    checkout_root = Path(__file__).resolve().parents[2]
    if all((checkout_root / tree_name).is_dir() for tree_name in RESOURCE_TREES):
        return checkout_root
    raise FileNotFoundError("AURORA default workspace resources are unavailable")


def _copy_missing(source: Any, destination: Path, root: Path) -> tuple[int, int]:
    created = 0
    skipped = 0
    for entry in source.iterdir():
        if entry.name == "__pycache__" or entry.name.endswith((".pyc", ".pyo")):
            continue
        target = destination / entry.name
        _ensure_inside_root(target, root)
        if entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            child_created, child_skipped = _copy_missing(entry, target, root)
            created += child_created
            skipped += child_skipped
        elif entry.is_file():
            if target.exists():
                skipped += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with entry.open("rb") as source_file, target.open("xb") as destination_file:
                destination_file.write(source_file.read())
            created += 1
    return created, skipped


def _ensure_inside_root(path: Path, root: Path) -> None:
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Workspace resource path escapes the requested root: {path}") from exc
