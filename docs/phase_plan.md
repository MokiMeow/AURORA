# AURORA-SE Production Readiness Phases

This roadmap breaks the build-out into concrete, production-grade phases. Each phase delivers auditable, fully operational capabilities before advancing. For high-level goals, refer to `plan.md`, which now links back to this roadmap.

## Phase 0 – Foundation & Environment
- Finalize repository scaffolding, deterministic dependency pinning, and virtual environment bootstrap.
- Stand up Docker Compose stack (Ollama, Postgres+pgvector with Milvus plugin, OTEL collector, Grafana, MinIO artifact store, optional Firecracker tools).
- Seed baseline configs (`/configs/model.yaml`, `/configs/tools.yaml`, `/configs/languages.yaml`, `/configs/hardware.yaml`, `/configs/sandbox.yaml`, `/configs/governance.yaml`).
- Provide sample monorepo under `/examples/` (TypeScript + Python + k6) and reference SBOM baseline.
- Add base GitHub Actions workflow (fast profile) plus pre-commit hooks enforcing lint/typecheck.
- Publish onboarding guide covering environment setup, secrets policy, deterministic seeds, coding standards, and PDCA expectations.

## Phase 1 – Repo Intelligence Layer (Production Ready)
- Implement tree-sitter based multi-language parsing (TypeScript, Python) with pluggable packs defined in `/configs/languages.yaml` and incremental sharding.
- Build code graph persistence (SQLite core with Neo4j adapter) capturing def/ref/call/import/test edges, symbol metadata, and test mappings.
- Integrate pgvector embeddings with automatic shard management for 100k+ files and optional Milvus backend; implement change detection/resumable jobs.
- Deliver context packer ranking graph slices, embeddings, experience vault hits, SWE-Bench telemetry, and policy notes.
- Emit PDCA `Plan` entries, OTEL traces, and structured logs for indexing runs; store failure taxonomy in `/telemetry/errors.jsonl`.
- Expose CLI `aurora-se index --full|--incremental` with retry taxonomy and artifact exports.

## Phase 2 – Planner & Critic Stack
- Implement planner client for DeepSeek-R1 via Ollama with streaming, retries, timeout budgets, and secret redaction filters.
- Enforce Self-Edit schema (pydantic) including CI profile hints, SBOM expectations, acceptance thresholds, and PDCA linkage.
- Integrate retrieval augmentation (graph context, embeddings, experience vault, SWE-Bench analytics, policy notes) with provenance tracking.
- Add critic orchestration (GPT-4o-mini, Gemini 2.5 Pro) with risk routing, compliance checklist, and structured feedback logging.
- Persist planner artifacts, retrieved context snapshots, critic outputs, and policy decisions in timestamped folders under `/artifacts/<run>/`.
- Extend CLI `aurora-se plan` with `--auto` and `--critic`, auto-retry recoverable errors, and governance logging.

## Phase 3 – Executor, Sandbox, and CI Orchestration
- Implement patch applier with dry-run, verification, rollback, diff explainers, and policy checks preventing unsafe test deletions.
- Provide sandbox manager supporting Docker and Firecracker (per `/configs/sandbox.yaml`) with egress controls, resource quotas, and artifact mounts.
- Build CI profile engine (fast/balanced/thorough) executing lint, unit, bandit, semgrep, typecheck, coverage, k6 smoke/endurance, fuzz (Atheris/Jazzer), SBOM diff (Syft), CVE scan (Grype), dependency audit, license scan, and custom security checks.
- Implement failure taxonomy (fatal/retryable), circuit breaker thresholds, and structured error logging (`/telemetry/errors.jsonl`).
- Integrate secret scanning (regex + TruffleHog), SBOM/CVE gating, license policy enforcement, and acceptance threshold validation (`security_zero_criticals`, `min_R`, complexity changes).
- Emit PDCA `Do`/`Check` events, OTEL metrics, and correlation IDs; support CLI `aurora-se apply --profile fast|balanced|thorough` for sandboxed execution and auto accept/revert.

## Phase 4 – Reward Engine & Experience Vault
- Implement metric collectors aggregating CI outputs (tests, coverage, perf latency, security score, cyclomatic complexity, policy bonuses).
- Compute scalar reward per `/configs/reward.yaml` with adaptive weighting, bias penalties, policy bonuses, and curriculum scheduler.
- Generate explainability reports (JSON/HTML) describing contribution breakdowns, attach to artifacts, and update PDCA `Check` entries.
- Expand experience vault (`/experience/log.jsonl`) with embeddings, reward outcomes, regret signals, policy notes, and bias metrics; expose retrieval API for planner conditioning.
- Enforce acceptance gates (`min_R`, zero critical security, complexity/bias thresholds) with audit logging; document override workflow requiring justification and governance approval.

## Phase 5 – Self-Learning & Adapter Management
- Build nightly Filtered-SFT pipeline using Hugging Face Transformers + PEFT/LoRA with bias detection, rejection sampling, and regularization.
- Integrate hardware auto-detection per `/configs/hardware.yaml`, supporting GPU (24 GB target) and CPU fallback (8-bit + gradient checkpointing).
- Version adapters under `/adapters/<domain>/<semver>/` with metadata (training metrics, bias scores, compliance status, provenance) and publish changelog.
- Extend CLI with `aurora-se learn`, `aurora-se adapters list|sync|rollback`, policy enforcement, and telemetry logging.
- Implement federated adapter/experience sync using `/configs/federation.yaml`, encryption, policy scanner, and governance approvals.
- Produce training documentation, workshops, and bias audit reports in `/docs/training/`.

## Phase 6 – Evaluation Harness & Benchmarks
- Integrate SWE-Bench Lite/Live (submodule) with dataset management, scenario scheduling, and CLI `aurora-se eval --suite swe-bench-lite|live|full`.
- Automate nightly/weekly/monthly evaluations via GitHub Actions (CI/staging/prod) with artifact uploads, PDCA linkage, and policy gating.
- Generate analytics (JSON, CSV, Plotly dashboards) stored under `/eval/results/` and `/docs/reports/`; feed Grafana panels.
- Correlate evaluation metrics with planner/executor versions, reward trends, and policy overrides; log in governance bundle.
- Ensure evaluation runs export SBOM diffs, compliance summaries, and telemetry snapshots.

## Phase 7 – Observability, Governance, and Compliance
- Finalize OTEL collector pipelines, Prometheus exporters, structured JSON logging with correlation IDs, and Grafana dashboards.
- Implement PDCA telemetry writer (`/telemetry/pdca.jsonl`), `aurora-se telemetry export`, and incident response runbooks.
- Automate governance bundle generation per `/docs/governance/compliance_bundle_template.md` including ethics charter, bias metrics, policy overrides, SWE-Bench trends, SBOM/CVE status.
- Deliver `aurora-se report --weekly` and `aurora-se governance bundle --period weekly` commands (HTML/PDF + JSON outputs).
- Provide operations/runbooks covering onboarding, sharding, reward tuning, sandbox failures, SRs, and compliance reviews; align with OWASP/ASVS guardrails.
- Ensure policy engine (`aurora-se policy check|set`) validates allow-lists, licenses, secrets, and security policies on every run.

## Phase 8 – Production Hardening & Launch
- Run chaos tests, load tests, fuzz campaigns, and failover drills across planner, executor, reward, learning, and telemetry subsystems.
- Conduct security review (penetration tests, dependency audits, CVE remediation) and document results in governance bundle.
- Execute end-to-end dry runs on 100k+ file monorepos to validate ≤15 min fast profile, ≤5 min incremental indexing, and auto accept/revert flows.
- Finalize environment rollouts (local, CI, staging, prod) with container images, deployment scripts, resource configs, and federation readiness.
- Define SLOs/SLA, monitoring alerts, on-call rotations, incident escalation paths, and maintenance windows.
- Publish v1.0.0 release package with release notes, migration guides, training certifications, and roadmap for symbolic reasoning, formal verification, and multi-agent critic ensemble.

