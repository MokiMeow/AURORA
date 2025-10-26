# AURORA-SE

Autonomous Unified Repo Orchestrator for Reasoning & Adaptation — Self-Editing.

## Overview

AURORA-SE is a self-adapting engineering system that plans, applies, verifies, and learns from code changes across large-scale monorepos. It orchestrates a PDCA loop backed by observability, governance, and compliance controls.

### Tech Stack Highlights
- Planner: DeepSeek-R1 via Ollama with optional GPT-4o-mini/Gemini critic stack
- Repo Intelligence: tree-sitter, pgvector, optional Milvus, Neo4j adapter
- Execution: Docker/Firecracker sandbox, CI profiles (fast/balanced/thorough)
- Observability: OpenTelemetry, Prometheus, Grafana dashboards
- Security: Syft, Grype, TruffleHog, license/policy engine
- Learning: Filtered-SFT with LoRA/PEFT adapters, federated sync
- Evaluation: SWE-Bench Lite/Live nightly/weekly suites

### Getting Started
1. Install dependencies: `pip install -e .[dev]`
2. Install hooks: `pre-commit install`
3. Start services: `docker compose up -d`
4. Run `aurora-se init` to bootstrap configs
5. See `docs/quickstart.md` for workflow details

