# Plan 001: Ship a complete installable workspace

> Executor instructions: Follow this plan exactly. Run each gate before the next step. Stop on a STOP condition instead of broadening scope. The reviewer updates `plans/README.md`.
>
> Drift check: `git diff --stat 843a5cdf9ba3c944f844e6eea78030a8a01857bb..HEAD -- pyproject.toml requirements-dev.lock LICENSE aurora/workspace cli/main.py aurora/planner/service.py tests/test_cli_init.py tests/test_packaging.py .github/workflows/ci-fast.yml README.md docs/quickstart.md`

## Status

- Priority: P1
- Effort: M
- Risk: MED
- Depends on: none
- Category: packaging / public readiness
- Planned at: `843a5cd`, 2026-07-22

## Why this matters

The published wheel currently contains Python modules but none of the default
configuration, policy, prompt, query, or automation resources required by the
documented CLI flow. `aurora-se init` creates only three empty runtime
directories. A user who installs the wheel and follows the quickstart therefore
hits missing `configs/*.yaml` files immediately. Merely importing the planner
also creates `artifacts/` in the current directory, so even `aurora-se --help`
has a filesystem side effect. The package declares Apache-2.0 but ships no
license text, and the unused `requirements-dev.lock` contradicts the active
tree-sitter compatibility pin.

## Current evidence

- `pyproject.toml:39-40` builds only `aurora` and `cli`.
- `cli/main.py:107-116` creates only `artifacts`, `telemetry`, and `experience`.
- `cli/main.py:124`, `142`, `216`, and other commands use repository-relative defaults under `configs/` and `policies/`.
- `aurora/planner/service.py:25-26` creates `artifacts/` at module import time.
- A clean wheel audit reported `HAS_CONFIGS=False`, `HAS_POLICIES=False`, `HAS_PROMPTS=False`, and `HAS_LICENSE=False`.
- `requirements-dev.lock` pins `tree-sitter==0.25.2`, while `pyproject.toml` intentionally pins `tree-sitter==0.20.4` for `tree-sitter-languages==1.10.2`; CI ignores the lock and installs from `pyproject.toml`.

## Scope

In scope:

- `pyproject.toml`
- `LICENSE` (new)
- `requirements-dev.lock` (remove the stale unused file)
- `aurora/workspace/bootstrap.py` (new)
- `aurora/workspace/__init__.py`
- `cli/main.py`
- `aurora/planner/service.py`
- `tests/test_cli_init.py`
- `tests/test_packaging.py` (new)
- `.github/workflows/ci-fast.yml`
- `README.md`
- `docs/quickstart.md`

Out of scope:

- Changing command names or removing existing CLI options.
- Shipping datasets, model weights, secrets, generated artifacts, or infrastructure credentials.
- Replacing the tree-sitter parser stack.
- Overwriting user-edited workspace files during initialization.

## Steps

### Step 1: Correct package metadata and bundle runtime templates

Add the complete Apache-2.0 license and reference it from project metadata. Add
project URLs and configure Hatch to place the existing `configs`, `policies`,
`prompts`, `queries`, and `scripts` trees under `aurora/resources/` in built
wheels. Do not package generated artifacts, telemetry, datasets, private keys,
or environment files. Remove the stale unused lock file and document that
`pyproject.toml` is the supported dependency source until a universal lock is
adopted.

Verify: build a wheel with `python -m pip wheel . --no-deps` and inspect it for
the resource trees plus a dist-info license entry.

### Step 2: Make init bootstrap a usable workspace

Add a small workspace bootstrap service based on `importlib.resources`. In a
source checkout it may fall back to the repository resource trees; in an
installed wheel it must use packaged resources. `aurora-se init --root <dir>`
must create runtime directories and copy missing default resources without ever
overwriting an existing file. Report created and skipped counts. Keep path
resolution inside the requested root.

Verify: `python -m pytest tests/test_cli_init.py` passes, including second-run
idempotence and preservation of a user-modified config.

### Step 3: Remove import-time filesystem mutation

Make planner artifact directory creation lazy and instance-scoped. Importing
`cli.main` or requesting help from an empty directory must not create
`artifacts/`, `telemetry/`, or any other file.

Verify: add a subprocess regression test that imports the CLI from an empty
working directory and asserts the directory remains empty.

### Step 4: Add a wheel smoke gate and public setup docs

Add a Python 3.12 CI step that builds the wheel, installs it into an isolated
target or virtual environment, runs `aurora-se init` in a temporary workspace,
and confirms the default config/policy/query resources exist. Update README and
quickstart with editable-development versus wheel-install workflows and the
non-overwrite behavior.

Verify: `python -m ruff check .`, `python -m mypy aurora cli`, and
`python -m pytest` all pass.

## Done criteria

- A built wheel contains the runtime resource trees and Apache-2.0 license.
- `aurora-se init` produces a usable workspace from an installed wheel.
- Re-running init never overwrites user changes.
- Import/help commands have no filesystem side effects.
- The stale contradictory lock file is gone and dependency guidance is truthful.
- Local and CI packaging smoke gates pass.

## STOP conditions

- Hatch cannot include the resource trees without duplicating secrets or generated data.
- Existing documented behavior requires init to overwrite user configuration.
- Wheel smoke needs network credentials, model downloads, Docker, or external services.
- Any verification command fails twice after a focused correction.
