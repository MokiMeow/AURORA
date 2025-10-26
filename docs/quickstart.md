# Quickstart

1. Install dependencies with `pip install -e .[dev]` and install pre-commit: `pre-commit install`.
2. Start local services using `docker compose up -d` (Ollama, Postgres+pgvector, Milvus, MinIO, OTEL collector, Grafana).
3. Initialize the workspace via `aurora-se init`.
4. Explore the sample monorepo under `examples/sample_repo/` for indexing demos.
5. Index the repository: `aurora-se index --full`.
6. Plan a change: `aurora-se plan --task "Fix failing login test" --auto --critic`.
7. Apply edits: `aurora-se apply --edit artifacts/self_edit.json --profile balanced`.
8. Review telemetry and artifacts under `artifacts/` and `telemetry/`.

