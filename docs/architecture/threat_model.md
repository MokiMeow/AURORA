# Aurora-SE Threat Model (Phase 1 Baseline)

This document summarizes the threat analysis after the Phase 1 sandbox & security hardening. The scope covers local developer environments running the Aurora-SE CLI with optional Docker Compose services and the hardened Docker/Firecracker runtimes.

## Assets and Trust Boundaries

| Asset | Notes | Trust Boundary |
|-------|-------|----------------|
| Source repositories | Primary codebase under automation | Workspace filesystem |
| Planner/executor credentials | API keys for model providers or package registries | Environment variables and config files |
| Telemetry and PDCA logs | Sensitive operational history | `telemetry/` directory and external collectors |
| Governance bundles | Compliance snapshots, SBOMs, adapter metadata | `docs/governance/` tree |
| Experience vault | Historical edits with reward metrics | `experience/log.jsonl` |

Trust boundaries exist between:
- User workstation and external APIs (model providers, package registries).
- Workspace and sandbox execution environments (Docker / Firecracker).
- Local system and optional remote telemetry collectors.

## STRIDE Analysis

### Spoofing
- **Risk:** Unauthenticated remote services impersonating model endpoints.
- **Mitigation:** TLS endpoints with pinned URLs in `configs/model.yaml`; API keys sourced from dedicated env vars per route; future work includes token validation and mTLS for self-hosted models.

### Tampering
- **Risk:** Malicious patches altering repository state outside PDCA flow.
- **Mitigation:** Executor relies on `git apply --check` dry runs, forbids test deletions, and writes diffs to artifacts for review. Sandbox policies restrict write access to workspace mounts.

### Repudiation
- **Risk:** Operators deny actions taken by the autonomous loop.
- **Mitigation:** Every phase logs PDCA entries to `telemetry/pdca.jsonl`, CI outputs are persisted under `artifacts/`, and governance bundles include run identifiers.

### Information Disclosure
- **Risk:** Secrets or proprietary code leaks through planner prompts or telemetry exports.
- **Mitigation:** Planner redaction uses configurable regex patterns before persisting sessions; executor secret scanning chains regex detection with TruffleHog/GitLeaks and path allow-lists; telemetry exports remain opt-in and default to local storage only.

### Denial of Service
- **Risk:** Long-running CI steps, runaway planners, or external API outages stall the loop.
- **Mitigation:** Planner has retry/backoff, executor circuits after repeated fatal failures, CI profiles specify timeouts, and evaluation pipeline captures exit codes for monitoring.

### Elevation of Privilege
- **Risk:** Code executed inside the sandbox escapes to the host.
- **Mitigation:** Docker runtime enforces read-only root, curated mounts, seccomp, optional AppArmor, and CPU/memory quotas. Firecracker sandbox launches disposable microVMs via `firectl`, copies workspace snapshots, and only enables tap devices when egress is allowed.

## Residual Risks (Phase 1)

- Firecracker relies on host tooling (`firectl`/`firecracker`); continuous integration must validate binary provenance.
- Model provider authentication still depends on operator-managed environment variables; secret rotation automation is pending.
- Incident response playbooks for sandbox breakout detection need to be exercised with real alerts.
- Signed artifact verification and supply-chain attestations remain future work.

## Next Steps

1. Automate signed artifact verification in executor and governance flow.
2. Expand incident response runbooks with telemetry-driven alerting drills.
3. Add automated rootfs attestation for Firecracker snapshots.
4. Integrate remote telemetry exporters with per-tenant encryption at rest.

This threat model should be revisited at the end of every major phase or when new integrations (cloud sandboxes, managed telemetry backends, federation peers) are introduced.
