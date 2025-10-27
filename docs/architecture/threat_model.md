# Aurora-SE Threat Model (Phase 0 Baseline)

This document summarizes the threat analysis completed during Phase 0. The scope covers local developer environments running the Aurora-SE CLI with optional Docker Compose services.

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
- **Mitigation:** TLS endpoints with pinned URLs in `configs/model.yaml`; future work includes token validation and mTLS for self-hosted models.

### Tampering
- **Risk:** Malicious patches altering repository state outside PDCA flow.
- **Mitigation:** Executor relies on `git apply --check` dry runs, forbids test deletions, and writes diffs to artifacts for review. Sandbox policies restrict write access to workspace mounts.

### Repudiation
- **Risk:** Operators deny actions taken by the autonomous loop.
- **Mitigation:** Every phase logs PDCA entries to `telemetry/pdca.jsonl`, CI outputs are persisted under `artifacts/`, and governance bundles include run identifiers.

### Information Disclosure
- **Risk:** Secrets or proprietary code leaks through planner prompts or telemetry exports.
- **Mitigation:** Planner redaction uses configurable regex patterns, executor secret scanning halts runs on detection, telemetry exports are opt-in and default to local storage only.

### Denial of Service
- **Risk:** Long-running CI steps, runaway planners, or external API outages stall the loop.
- **Mitigation:** Planner has retry/backoff, executor circuits after repeated fatal failures, CI profiles specify timeouts, and evaluation pipeline captures exit codes for monitoring.

### Elevation of Privilege
- **Risk:** Code executed inside the sandbox escapes to the host.
- **Mitigation:** Local sandbox uses least-privilege execution; Phase 1 will introduce hardened Docker and Firecracker profiles (seccomp, read-only mounts, network isolation).

## Residual Risks (Phase 0)

- Firecracker runner operates in passthrough mode; hardening is tracked for Phase 1.
- Model provider authentication depends on environment variables; secret rotation automation is pending.
- Telemetry exports to remote collectors require manual configuration and review.

## Next Steps

1. Harden Firecracker/Docker isolation (Phase 1).
2. Add signed artifact verification in executor policy checks.
3. Implement secret scanning allow/deny lists synchronized with governance policy decisions.
4. Integrate incident response runbooks with telemetry alerting.

This threat model should be revisited at the end of every major phase or when new integrations (cloud sandboxes, managed telemetry backends, federation peers) are introduced.

