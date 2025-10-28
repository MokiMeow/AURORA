# Phase 4 - Reward Engine & Experience Vault Validation

## Scope

Phase 4 replaces heuristic reward scoring with telemetry-driven signals, persists experience vault data with governance-grade indices, and publishes explainability artefacts for downstream consumers.

## Deliverables Verified

- Reward configuration schema (`configs/schemas/reward.schema.json`) and loader (`aurora/reward/config_loader.py`) yield typed `RewardConfig` objects with tunable weights, penalties, and regression controls.
- Metric ingestion parses CI artefacts (tests, coverage, latency, security, complexity, bias) while tracking a rolling history for adaptive scheduling.
- Adaptive scheduler now supports `windowed`, `ucb1`, and `epsilon_greedy` strategies with exploration knobs and weight safeguards.
- Reward calculator emits structured explainability via `RewardReportWriter`, generating JSON + HTML dashboards under `artifacts/reward_reports/`.
- Experience vault enforces dedupe, retention, redaction, and metadata indices (`task_index.json`, `top_rewards.json`, `policy_index.json`).
- Public `RewardAPI` exposes latest reward snapshots, history windows, and summaries for dashboards or downstream ML.
- Regression harness (`RewardEngine.run_regression_suite`) compares expected vs actual rewards using fixtures in `tests/fixtures/reward_runs/`.
- Typer CLI command `aurora-se reward --ci-results <file>` wires the service, explainability outputs, and regression workflow for operators.

## Automated Verification

```bash
pytest -k reward
```

The suite covers configuration loading, collectors, scheduler strategies, explainability reporting, experience vault indices, regression harness, reward API/service, and engine integration. All tests pass (`17 passed`).

## Manual Checks

- Generated explainability artefacts under `artifacts/reward_reports/` (`latest_reward.json`, `latest_reward.html`, `reward_trend.html`).
- Confirmed experience vault indices populate under `experience/indices/` during engine execution.
- Validated regression fixture `tests/fixtures/reward_runs/ci_success.json` matches expected reward (6.9) with tolerance 0.2.
- Verified CLI invocation `aurora-se reward --ci-results artifacts/ci_results.json --summary --history 5` prints reward decision and refreshes explainability folder.

## Exit Criteria

- [x] Reward configuration + schema validated.
- [x] Adaptive scheduler reacts to reward history without destabilising weights.
- [x] Explainability outputs provide per-component transparency and historical trend view.
- [x] Experience vault retains unique, sanitised entries with task/reward/policy indices.
- [x] Regression, API, and CLI endpoints operational for downstream automation.

Phase 4 is production-ready; proceed to Phase 5 planning per `plan.md`.
