# DeepSeek-R1 Demo Walkthrough

This guide shows how to use AURORA-SE with a locally running DeepSeek-R1 planner to detect and fix the bug in `examples/demo/`.

## Prerequisites

1. DeepSeek-R1 7B model warmed locally (default Ollama endpoint `http://localhost:11434/api/generate`).
2. Demo monorepo prepared: `examples/demo/`.
3. Virtual environment with AURORA-SE installed in editable mode.

## 1. Index the Demo Repo

```bash
aurora-se index --full --root examples/demo --config configs/indexer.yaml
```

You should see PDCA entries in `telemetry/pdca.jsonl` documenting the indexing run.

## 2. Generate a Plan with Critic

```bash
aurora-se plan --task "fix failing add test" --auto --critic --config configs/model.yaml
```

* DeepSeek-R1 returns a plan pointing at `pycalc/calc.py`.
* Critic feedback is logged under `artifacts/<timestamp>/critic/`.

## 3. Apply the Self-Edit

```bash
aurora-se apply --edit examples/demo/self_edit.json --profile fast
```

Before applying, you can see the failing test:

```bash
pytest examples/demo/tests/test_calc.py
# fails: assert -1 == 5
```

During execution you’ll see:

- Secret scanning results.
- CI outcomes (`pytest`, lint, etc.).
- Reward report deposited in `artifacts/<timestamp>/reward/`.

## 4. Observe Improvements

Review `artifacts/<timestamp>/executor_summary.json` for CI and policy results. The reward report illustrates:

- Positive `Δtests_passed` (failing test fixed).
- Bias/security checks remaining green.

## 5. Report and Governance

```bash
aurora-se eval --suite swe-bench-lite
aurora-se telemetry --export
aurora-se governance bundle
```

These commands refresh evaluation metrics, emit telemetry snapshots, and update governance bundles with the new successful run.

## Summary of Improvements

- `pycalc.calc.add` now returns `a + b` instead of subtraction.
- Unit tests pass, restoring expected functionality.
- Telemetry and governance artifacts capture the full PDCA loop for auditability.
