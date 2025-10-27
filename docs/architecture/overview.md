# Aurora-SE Architecture Overview

This document captures the current production architecture for Aurora-SE after the Phase 0 hardening pass. It expands on the summary in `plan.md` and provides component-level responsibilities plus the data flows that enable the PDCA loop.

## System Context

- **CLI / Operators** invoke `aurora-se` commands that orchestrate the PDCA cycle.
- **Model Providers** supply planning, critic, and learning inference (DeepSeek-R1 plus optional GPT critics).
- **Execution Substrate** (local sandbox, Docker, or Firecracker) applies code edits and runs CI profiles.
- **Persistence Layer** stores repository intelligence (SQLite/pgvector), telemetry logs, governance bundles, and experience records.
- **Observability Stack** exports Prometheus metrics, OTEL traces, and PDCA logs for audit trails.

All components operate in a workspace root with sandboxed execution boundaries; long-running services (Ollama, Postgres, MinIO) run via Docker Compose when the operator enables them.

## Core Services

### Indexer (`aurora.indexer`)
- Parses repositories with Tree-sitter, constructs a semantic graph, and persists it via SQLite (with optional Neo4j for visualization).
- Generates embeddings with deterministic hashing so planner retrieval does not require heavyweight model calls during Phase 0.
- Publishes symbol, import, and call neighbors consumed by the planner context packer.

### Planner (`aurora.planner`)
- Loads planner configuration (primary model, critics, retry policy, secret redaction).
- Builds prompts by combining repository intelligence, telemetry snippets, and the experience vault.
- Emits PDCA events for every planning run and persists artifacts (`artifacts/planner_output.txt`, `artifacts/self_edit.json`, critic feedback).

### Executor (`aurora.executor`)
- Applies patches through `git apply` with a dry-run guard, rejects edits that delete tests, and scans for secrets before running CI.
- Runs CI profiles through sandbox runners (local, Docker, Firecracker placeholder) and enforces policy gates defined in `policies/security.yaml`.
- Records PDCA entries for "Do -> Check -> Act", including CI summaries, policy outcomes, and a consolidated `artifacts/executor_summary.json`.

### Reward Engine (`aurora.reward`)
- Converts CI results into reward snapshots, enforces policy thresholds, and appends decisions to the experience vault.
- Schedules adaptive learning runs and emits Prometheus metrics for downstream dashboards.

### Learning (`aurora.learn`)
- Manages adapter registries, nightly LoRA fine-tuning workflows, and optional federation sync.
- Writes bias reports and PDCA entries so governance reviewers understand model drift risk.

### Evaluation (`aurora.eval`)
- Orchestrates SWE-Bench suites, produces compliance bundles, and publishes dashboards under `docs/reports/`.
- Generates SBOM diffs and telemetry snapshots that feed governance decisions.

### Telemetry and Governance
- `aurora.telemetry` sets up logging, OTEL export, and Prometheus emitters for consistent observability across subsystems.
- `aurora.governance` assembles compliance bundles and reports consumed by operations and audit teams.

## Data Flows

1. **Plan:** Planner reads repo graph and embeddings, supplements with experience vault context, generates `self_edit.json`, and logs PDCA events.
2. **Do:** Executor applies patches inside the configured sandbox, runs the requested CI profile, and logs outputs to artifacts.
3. **Check:** Reward engine ingests CI results, computes reward plus metrics, and triggers evaluation pipelines as required.
4. **Act / Learn:** Learning service updates adapters, pushes federation changes (if enabled), and records telemetry and governance artifacts.

All stages append to `telemetry/pdca.jsonl`, ensuring the operations team can reconstruct every automation attempt.

## Security and Isolation Baseline

- Local sandbox is hardened with secret scanning, policy enforcement, and test-deletion guards.
- Docker sandbox (Phase 1 target) will add mount controls and optional network isolation.
- Firecracker sandbox currently logs a warning (Phase 1 upgrade) but enforces the same policy and secret checks.

## Dependencies

- Python 3.11 runtime with Typer CLI.
- Tree-sitter bindings plus pgvector / SQLite for repository intelligence.
- Optional Neo4j, Prometheus, Grafana, and OTEL collector for advanced deployments.
- Security tooling (Bandit, Semgrep, Grype) referenced in CI profiles and policies.

This architecture baseline will evolve in later phases (sandbox hardening, telemetry multi-tenancy, federated learning). Updates should be reflected here and cross-referenced from `docs/phase_plan.md` and `plan.md`.

