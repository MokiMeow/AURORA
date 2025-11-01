# Autopilot Command

urora-se autopilot --task <task> orchestrates plan ? apply ? reward ? eval with guardrails:

- --max-iterations — stop after N PDCA cycles.
- --max-cost — abort if estimated token cost exceeds the budget.
- --seed — deterministic scheduling for repeatable tests.
- --plugin — load extension hooks.
- --dry-run — skip executor side effects.
- --require-confirm — prompt before applying changes.

Artifacts are written into the active session directory and tracked via telemetry.

