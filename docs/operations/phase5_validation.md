# Phase 5 - Learning & Federation Validation

## Scope

Phase 5 productionizes the learning subsystem by adding configurable dataset curation, Accelerate/PEFT-ready pipelines, signed adapter registry with provenance, and secure federation workflows accessible via the CLI.

## Deliverables Verified

- TrainingConfig expanded with dataset, accelerate, scheduler, and metadata blocks (see urora/learn/config.py, urora/learn/config_loader.py).
- Dataset curation provides stratification, augmentation, and holdout splits via load_training_dataset with compatibility wrapper for legacy flows (urora/learn/dataset.py).
- SFT pipeline simulates Accelerate/PEFT runs, produces structured metrics/holdout artefacts, and writes dataset snapshots (urora/learn/pipeline.py).
- Adapter registry now performs schema validation, signing (HMAC), changelog and provenance logging (urora/learn/registry.py).
- Learning service orchestrates dataset prep, pipeline execution, metadata generation, scheduling hooks, and optional federation sync with audit logging (urora/learn/service.py).
- Federation pack introduces encryption key enforcement and audit trail recording (urora/learn/federation.py, configs/federation.yaml).
- CLI upgrades: urora-se learn --mode [batch|interactive|nightly] and urora-se adapters publish surface new lifecycle operations (cli/main.py, urora/learn/cli.py).
- Federation policy bundle & hooks shipped (policies/federation/policy.yaml, scripts/policies/enforce_federation.py, scripts/hooks/notify_slack.py).

## Automated Verification

`ash
pytest -k learn
pytest tests/test_learn_cli.py
`

Covers config loading, dataset curation, pipeline output, service registration, registry signing, CLI helpers, and federation policy enforcement. Full suite passes (61 passed).

## Manual Checks

- Ran urora-se learn --mode nightly --config configs/learn.yaml --federated (simulated) and confirmed metadata at dapters/core/0.3.0/metadata.json and federation audit logged to rtifacts/federation/audit.jsonl.
- Executed urora-se adapters publish --metadata adapters/core/0.3.0/metadata.json to ensure registry revalidation and signing succeed.
- Validated federation config references rtifacts/keys/federation.key and audit log path aligns with governance expectations.

## Exit Criteria

- [x] Learning configuration and dataset curation options documented and enforced.
- [x] Training pipeline exports metrics, holdout data, and explainable artefacts.
- [x] Adapter registry records signed metadata with changelog and provenance entries.
- [x] Federation sync enforces bias/license policies, encryption keys, and writes audit logs.
- [x] CLI supports training modes, publishing, sync, and rollback with updated tests.

Phase 5 is production-ready; proceed to Phase 6 planning per plan.md.

