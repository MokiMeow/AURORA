# Phase 7 - CLI/UX & Extension Ecosystem Validation

## Scope

Phase 7 delivers a production-grade Aurora-SE CLI, interactive shell, workspace automation, notification stack, plugin marketplace, and governance/telemetry integrations needed for PDCA autopilot experiences.

## Deliverables Verified

- Full CLI command surface aligned with plan.md (autopilot, shell, session, workspace, plugin, policy, report, telemetry, notify, api, scripts, governance, model management).
- / shell commands cover context, model switching, critic toggles, session management, workspace snapshots, autopilot launch, plugin live controls, telemetry log tailing, reward inspection, and policy checks (aurora/cli/shell.py, cli/main.py).
- Autopilot guardrails and reporting implemented with iteration/cost ceilings and deterministic seeds (aurora/autopilot/service.py, cli/main.py).
- Plugin SDK extended with registry management, signatures, publication, and config synchronization (aurora/extensions/registry.py, aurora/extensions/__init__.py, cli/main.py).
- Workspace snapshot manager provides snapshot/restore/status flows (aurora/workspace/manager.py, cli/main.py).
- Governance/telemetry/policy/notification subcommands integrate compliance bundles, dashboards, policy profiles, and outbound channels (aurora/governance/reports.py, aurora/notify/service.py, configs/policy_profiles.yaml, configs/notify.yaml).
- Model manager enables list/switch/test workflows for routing (aurora/planner/model_manager.py, cli/main.py).
- Documentation for new surface in docs/cli/ plus updated governance bundle templates docs/governance/bundles/lite_latest.json and generated reporting artifacts (docs/reports/).
- Phase 7 validation now includes CLI help/docs, plugin registry assets, autopilot workflow templates, and UX guidance per plan.

## Automated Verification

```bash
pytest -k "cli or autopilot or workspace or plugin"
pytest
```

The targeted run exercises CLI entry points (autopilot, shell, plugin, session, workspace, policy, report, notify, telemetry, api) and supporting services. The full suite passes locally.

## Manual Checks

- aurora-se shell --script "/context;/model ollama_primary;/critic on;/workspace snapshot phase7;/quit" confirms shell slash commands and workspace snapshots.
- aurora-se autopilot --task "refactor config" --dry-run --max-iterations 2 --format markdown generates guarded PDCA artifacts and Markdown summary.
- aurora-se plugin install demo --spec demo_ext:Demo --source extensions registers plugin, aurora-se plugin publish demo emits signed manifest, and /plugin list reflects state instantly.
- aurora-se workspace status shows snapshot counts after shell-triggered save/restore flows.
- `aurora-se policy list` and `aurora-se policy check --results ci.json --metadata evidence.json` operate against configured profiles using explicit evidence files.
- aurora-se telemetry dashboard --export exports dashboard metadata without duplicating Prometheus collectors.
- aurora-se governance bundle --evaluation docs/governance/bundles/lite_latest.json --output artifacts/bundles/current.json followed by governance policy validates compliance.
- aurora-se notify slack "Release cut" logs outbound message audit trail.

## Exit Criteria

- [x] CLI exposes plan.md Phase 7 commands with help text, docs, telemetry overlays, and autopilot controls.
- [x] Interactive shell supports documented slash commands including autopilot launch, workspace/session tooling, and plugin management.
- [x] Plugin SDK + registry provide install/remove/list/sign/publish plus config bridging and signatures.
- [x] Workspace, governance, policy, report, notify, telemetry, api, and model managers ship with automated tests and docs.
- [x] Automated CLI integration tests and the full suite pass.
- [x] Documentation added for CLI usage, workflow templates, and updated governance bundle examples.

Phase 7 is production-ready; subsequent work may proceed to Phase 8.
