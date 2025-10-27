# Phase Readiness Backlog Snapshot

This document tracks follow-up items discovered during Phase 0 and Phase 1. Each entry should be mirrored as an issue in the primary tracker when available.

## Completed

- [x] Fix planner initialization ordering and experience vault wiring.
- [x] Add missing planner client imports for retry and critic authentication.
- [x] Align context packer with graph store and experience vault APIs.
- [x] Parse executor policies from YAML and update security baseline.
- [x] Import Firecracker sandbox in the CLI runtime for profile selection.
- [x] Refresh CI profiles to use available tooling and ensure type checking is enforced in GitHub Actions.
- [x] Publish refreshed architecture overview and threat model documents.
- [x] Harden Docker sandbox with seccomp/AppArmor, read-only mounts, and resource quotas.
- [x] Implement Firecracker microVM runner with snapshot copying and egress policy.
- [x] Integrate composite secret scanning (regex + TruffleHog/GitLeaks) with allow-lists.
- [x] Expand security policy DSL with license allow-list, SBOM/CVE gating, and CI enforcement.
- [x] Emit SBOM/CVE/license artifacts during CI and feed them into governance bundles.

## In Progress / Planned

- [ ] Automate incident response runbooks tied to telemetry alerts.
- [ ] Integrate signed artifact verification into executor policy gates.
- [ ] Add rootfs attestation for Firecracker snapshots.
- [ ] Formalize sandbox penetration testing cadence (document schedule + tooling).
- [ ] Package backlog items into GitHub issues with owners and target milestones.

This backlog should be reviewed at each phase boundary and updated as new risks or dependencies are discovered.
