# Aurora-SE Architecture Overview

This document captures the production architecture for Aurora-SE after the Phase 1 sandbox & security hardening. It expands on the summary in `plan.md` and provides component-level responsibilities plus the data flows that enable the PDCA loop.

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
- Loads planner configuration (primary model, routing rules, critics, retry policy, secret redaction).
- Builds prompts by combining repository intelligence, telemetry snippets, and the experience vault, then routes the request via `PlannerRouter` to the appropriate provider (Ollama, OpenAI, Anthropic, Google) with configurable consensus across critics.
- Emits PDCA events for every planning run, persists planner sessions (`artifacts/planner_sessions/`), and archives sanitized artifacts (`artifacts/planner_output.txt`, `artifacts/self_edit.json`, critic feedback).

#### Provider HTTP contract

The planner uses JSON over `httpx` directly; no provider SDK is required. The
bundled default route is local Ollama. Cloud routes and cloud critics remain
opt-in: operators must configure their endpoints/routes and provide credentials
through the environment. No credentials are stored in `configs/model.yaml`.

| Provider | Authentication | Supported responses |
| --- | --- | --- |
| Ollama | None for the bundled local route | JSON or `application/x-ndjson` |
| OpenAI | `Authorization: Bearer` from the route's `api_key_env` (sample: `OPENAI_API_KEY`) | JSON or server-sent events |
| Anthropic | `x-api-key` from `api_key_env` (sample: `ANTHROPIC_API_KEY`) plus `anthropic-version` | Messages JSON or text-delta server-sent events |
| Gemini | `x-goog-api-key` from `api_key_env` (sample: `GEMINI_API_KEY`) | Candidate JSON or candidate server-sent events |

Critics declare their provider explicitly. The sample disabled critics use
`CRITIC_GPT4O_API_KEY` and `CRITIC_GEMINI_API_KEY`. If any selected cloud route
or enabled critic names a credential environment variable that is absent, the
request fails before network I/O. Error messages never include credential or
response-body values.

Anthropic routes default to API version `2023-06-01`; set
`extra.api_version` on a route to select another supported version. Streaming
parsers ignore terminal markers, accumulate usable text chunks, and reject
provider error records or successful responses that contain no usable text.

Planner retries are limited to transport/timeouts and HTTP 408, 425, 429, and
5xx responses. Other 4xx responses fail after one request. Exponential backoff
and valid `Retry-After` delays are capped at 60 seconds and attempts never
exceed `retry_policy.max_attempts`.

### Executor (`aurora.executor`)
  - Applies patches through `git apply` with a dry-run guard and three-way merge fallback, rejects edits that delete tests, and scans for secrets (regex + TruffleHog/GitLeaks backends) before running CI.
  - Runs CI profiles through hardened sandbox runners (local process isolation, Docker with seccomp/AppArmor/read-only root, and Firecracker microVMs launched via `firectl`) while enforcing policy gates defined in `policies/security.yaml` and persisting security artifacts (SBOM, CVE, license reports).
  - Captures diff explainers, manual approval checkpoints, drift detection, and per-step CI telemetry (durations, retries, correlation IDs) under `artifacts/` and PDCA logs.

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

1. **Plan:** Planner reads repo graph and embeddings, supplements with experience vault context, selects a model route via `PlannerRouter`, generates `self_edit.json`, and logs PDCA events plus session trails.
2. **Do:** Executor applies patches inside the configured sandbox, runs the requested CI profile, and logs outputs to artifacts.
3. **Check:** Reward engine ingests CI results, computes reward plus metrics, and triggers evaluation pipelines as required.
4. **Act / Learn:** Learning service updates adapters, pushes federation changes (if enabled), and records telemetry and governance artifacts.

All stages append to `telemetry/pdca.jsonl`, ensuring the operations team can reconstruct every automation attempt.

## Security and Isolation Baseline

- Local sandbox is primarily used for development loops; production profiles rely on container or microVM isolation.
- Docker sandbox runs with a read-only root filesystem, controlled mount list, seccomp profile, optional AppArmor confinement, and CPU/memory quotas.
- Firecracker sandbox launches disposable microVMs via `firectl`, copies workspace snapshots, and honours network egress policy (tap devices only when explicitly enabled).

## Dependencies

- Python 3.11 runtime with Typer CLI.
- Tree-sitter bindings plus pgvector / SQLite for repository intelligence.
- Optional Neo4j, Prometheus, Grafana, and OTEL collector for advanced deployments.
- Security tooling (Bandit, Semgrep, Syft, Grype, Pip-Licenses) referenced in CI profiles and policies.

This architecture baseline will evolve in later phases (sandbox hardening, telemetry multi-tenancy, federated learning). Updates should be reflected here and cross-referenced from `docs/phase_plan.md` and `plan.md`.

