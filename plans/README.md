# AURORA implementation plans

Generated from the `improve` audit on 2026-07-22. Execute in order, keep each
change inside its listed scope, and run every verification gate before moving
to the next plan. The reviewer owns this status table.

## Execution order and status

| Plan | Title | Priority | Effort | Depends on | Status |
| --- | --- | --- | --- | --- | --- |
| 001 | Ship a complete installable workspace | P1 | M | - | DONE |
| 002 | Correct planner provider protocols and retries | P1 | M | - | DONE |
| 003 | Make executor failures transactional | P1 | M | - | BLOCKED — safe non-mutating three-way preflight could not be proven |
| 004 | Turn local API controls into a real loopback service | P2 | M | 001 | BLOCKED — verification failed twice under the plan stop rule |

Status values: TODO | IN PROGRESS | DONE | BLOCKED (with reason) | REJECTED
(with rationale).

## Audit baseline

- Base commit: `843a5cdf9ba3c944f844e6eea78030a8a01857bb`.
- Ruff passed, mypy passed for 93 source files, and pytest reported 99 passed / 1 skipped.
- Evaluation smoke, `pip check`, and `pip-audit` passed; no known dependency vulnerabilities were found.
- Coverage was 77 percent overall. The selected plans target confirmed runtime and packaging behavior, not low-coverage code merely for its own sake.
- A built wheel contained 97 entries but no `configs/`, `policies/`, `prompts/`, queries, scripts, or license file.

## Findings considered but deferred

- Real non-simulated PEFT training: the current learning pipeline produces simulated metrics and an empty adapter artifact even when the optional backend is present. A correct real trainer needs model/data policy, resource budgets, and a supported artifact contract; do not invent those choices in this pass.
- Full non-dry-run autopilot wiring: the current service writes plan/apply stubs and ignores planner/executor configuration, but the configured Docker executor image is not shipped and the fast profile requires external tools that are not installed by the documented setup. Connecting automatic code mutation before those runtime choices are resolved would be unsafe.
- Remote/public API exposure: Plan 004 is deliberately loopback-only. Authentication, multi-user state, TLS, and a stable remote API contract require a separate product decision.
- Replacing tree-sitter: `tree-sitter-languages` is current at 1.10.2 and relies on the older tree-sitter API. Keep the explicit `tree-sitter==0.20.4` compatibility pin until the parser stack is migrated together.
