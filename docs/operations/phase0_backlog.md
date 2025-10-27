# Phase 0 Backlog Snapshot

This document tracks the actionable items identified during the Phase 0 audit. Each entry should be mirrored as an issue in the primary tracker when available.

## Completed

- [x] Fix planner initialization ordering and experience vault wiring.
- [x] Add missing planner client imports for retry and critic authentication.
- [x] Align context packer with graph store and experience vault APIs.
- [x] Parse executor policies from YAML and update security baseline.
- [x] Import Firecracker sandbox in the CLI runtime for profile selection.
- [x] Refresh CI profiles to use available tooling and ensure type checking is enforced in GitHub Actions.
- [x] Publish refreshed architecture overview and threat model documents.

## In Progress / Planned

- [ ] Harden Firecracker sandbox isolation (Phase 1 deliverable).
- [ ] Automate incident response runbooks tied to telemetry alerts.
- [ ] Integrate signed artifact verification into executor policy gates.
- [ ] Expand secret scanning allow/deny lists with governance approval.
- [ ] Package backlog items into GitHub issues with owners and target milestones.

This backlog should be reviewed at each phase boundary and updated as new risks or dependencies are discovered.

