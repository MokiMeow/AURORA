# AURORA-SE

Autonomous Unified Repo Orchestrator for Reasoning & Adaptation — Self-Editing.

## Overview

AURORA-SE is a self-adapting engineering system that plans, applies, verifies, and learns from code changes across large-scale monorepos. It orchestrates a PDCA loop backed by observability, governance, and compliance controls.

### Tech Stack Highlights

- Planner: DeepSeek-R1 via Ollama with optional GPT-4o-mini/Gemini critic stack
- Repo Intelligence: tree-sitter, pgvector, optional Milvus, Neo4j adapter
- Execution: Docker/Firecracker sandbox, CI profiles (fast/balanced/thorough)
- Observability: OpenTelemetry, Prometheus, Grafana dashboards
- Dependency evidence: CycloneDX, pip-audit, pip-licenses, and the policy engine
- Learning: Filtered-SFT with LoRA/PEFT adapters, federated sync
- Evaluation: deterministic CI smoke coverage plus manually provisioned SWE-Bench suites

### Getting Started

1. Use Python 3.10–3.13 and create a virtual environment.
2. Install the project and development tools: `python -m pip install -e '.[dev]'`.
3. Prepare runtime directories: `aurora-se init`.
4. Run checks: `python -m ruff check .`, `python -m mypy aurora cli`, and `python -m pytest`.
5. Optionally install Git hooks with `pre-commit install` and start local services with `docker compose up -d`.
6. See `docs/quickstart.md` for the full local workflow.

SWE-Bench workflows are manual by design. Before dispatching one, place the corresponding licensed dataset and runner under `datasets/swe-bench-*`; the workflow validates those inputs and fails clearly when they are absent.

