# AURORA-SE Architecture

This document describes the high-level architecture for AURORA-SE.

## Overview

AURORA-SE implements a closed-loop PDCA cycle across planner, executor, reward, and learning subsystems. Each component emits telemetry and governance artifacts for traceability.

### Phase 0 Components
- Docker Compose stack orchestrates Ollama, Postgres+pgvector (with optional Milvus), MinIO, OTEL collector, and Grafana.
- Sample monorepo under `examples/` used for indexing and CI dry-runs.
- Baseline configs define language packs, model endpoints, sandbox policies, and telemetry routes.

