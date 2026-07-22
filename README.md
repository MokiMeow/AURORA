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

Use Python 3.10–3.12 and create a virtual environment. For development from a
source checkout, install the project and development tools in editable mode:

```shell
python -m pip install -e '.[dev]'
aurora-se init
python -m ruff check .
python -m mypy aurora cli
python -m pytest
```

For use from a built wheel, install the wheel and initialize a workspace at the
directory where you want to run AURORA-SE:

```shell
python -m pip install aurora_se-0.1.0-py3-none-any.whl
aurora-se init --root /path/to/workspace
```

Initialization creates the runtime directories and copies the bundled default
configurations, policies, prompts, queries, and automation scripts. It copies
only missing files, so re-running `init` preserves user changes. `pyproject.toml`
is the supported dependency source until the project adopts a universal lock
file.

Optionally install Git hooks with `pre-commit install` and start local services
with `docker compose up -d`. See `docs/quickstart.md` for the full local workflow.

SWE-Bench workflows are manual by design. Before dispatching one, place the corresponding licensed dataset and runner under `datasets/swe-bench-*`; the workflow validates those inputs and fails clearly when they are absent.
