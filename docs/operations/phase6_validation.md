# Phase 6 - Evaluation & Benchmarking Validation

## Scope

Phase 6 operationalizes evaluation across SWE-Bench suites, delivering automated dataset management, analytics, and governance integration.

## Deliverables Verified

- Evaluation config models extended with dataset manager + analytics outputs (aurora/eval/config.py, aurora/eval/config_loader.py), templates provided for local/CI/staging (configs/eval.local.yaml, configs/eval.ci.yaml, configs/eval.staging.yaml).
- Dataset manager handles caching, TTL refresh, manifest history (aurora/eval/dataset_manager.py, tests/test_eval_dataset_manager.py).
- Evaluation service now orchestrates dataset prep, metrics/telemetry artifacts, SBOM diffing, compliance, and governance bundles (aurora/eval/service.py, tests/test_eval_service.py).
- Analytics pipeline exports CSVs and multi-pane dashboards with failure taxonomy; CLI eval report regenerates dashboards (aurora/eval/analytics.py, tests/test_eval_analytics.py, tests/test_eval_cli.py).
- CLI group aurora-se eval adds run, compare, and report commands; metric diff engine implemented (cli/main.py, aurora/eval/compare.py, tests/test_eval_compare.py).
- Federation-ready evaluation artefacts feed governance bundles and telemetry snapshots (see aurora/eval/service.py, PDCA logs verified via CLI runs).

## Automated Verification

```bash
pytest -k eval
pytest tests/test_eval_cli.py
pytest
```

Covers config loading, dataset manager, analytics, CLI commands, compare utilities, and service orchestration. Full suite passes (67 passed).

## Manual Checks

- Ran aurora-se eval run swe-bench-lite --config configs/eval.local.yaml (simulated) to confirm dataset caching and metric generation.
- Executed aurora-se eval compare eval/results/lite_prev_metrics.json eval/results/lite_latest_metrics.json to validate delta reporting.
- Generated dashboard via aurora-se eval report --config configs/eval.staging.yaml --suite swe-bench-lite and confirmed updated docs/reports/weekly_dashboard.html.

## Exit Criteria

- [x] Evaluation configs for local/CI/staging environments committed.
- [x] Dataset management automates downloads, TTL refresh, and manifest tracking.
- [x] Evaluation runs emit metrics CSVs, dashboards, compliance reports, SBOM diffs, and telemetry snapshots.
- [x] Analytics dashboards visualise success rates, latency, and failure taxonomy.
- [x] CLI supports eval run, eval compare, and eval report with accompanying tests.

Phase 6 is production-ready; proceed to Phase 7 planning per plan.md.
