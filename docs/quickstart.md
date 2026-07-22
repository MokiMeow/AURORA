# Quickstart

## Develop from a source checkout

1. Use Python 3.10–3.12 and create a virtual environment.
2. Install dependencies with `python -m pip install -e '.[dev]'`.
3. Optionally install the Git hooks with `pre-commit install`.
4. Initialize the checkout with `aurora-se init`.
5. Start local services using `docker compose up -d` (Ollama, Postgres+pgvector, Milvus, MinIO, OTEL collector, Grafana).

`pyproject.toml` is the supported dependency source for development and CI. The
project does not currently maintain a universal lock file.

## Install a wheel

Install a locally built or downloaded wheel, then initialize the directory that
will hold the AURORA-SE workspace:

```shell
python -m pip install aurora_se-0.1.0-py3-none-any.whl
aurora-se init --root /path/to/workspace
cd /path/to/workspace
```

The wheel includes the default `configs/`, `policies/`, `prompts/`, `queries/`,
and `scripts/` trees. Initialization also creates `artifacts/`, `telemetry/`,
and `experience/`. Existing files are skipped, so re-running the command never
overwrites user-edited configuration.

## Run the workflow

1. Explore the sample monorepo under `examples/sample_repo/` for indexing demos when working from a checkout.
2. Index the repository: `aurora-se index --full`.
3. Plan a change: `aurora-se plan --task "Fix failing login test" --auto --critic`.
4. Apply edits: `aurora-se apply --edit artifacts/self_edit.json --profile balanced`.
5. Review telemetry and artifacts under `artifacts/` and `telemetry/`.
