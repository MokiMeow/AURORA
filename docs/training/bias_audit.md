# Bias Audit Process

This document defines the nightly bias audit workflow executed by `aurora-se learn`.

## Data Selection
- Only experiences with `reward >= min_reward` are included.
- Samples are randomly shuffled and truncated to `sample_size` to maintain deterministic batch sizes.
- Regret entries are excluded automatically.

## Heuristic Bias Scan
- The Filtered-SFT pipeline scans prompts and completions for protected-class indicators (gender, ethnicity, age).
- The ratio of hits to total samples yields a `bias_score` persisted in `bias_report_path`.
- Thresholds are defined in `configs/learn.yaml` (`max_bias_score`).

## Remediation Workflow
- If `bias_score > max_bias_score`, a `bias_warning` PDCA event is logged and the adapter is tagged for manual review.
- The governance team reviews generated `bias_reports/*.json` artifacts and may block adapter promotion via policy tools.
- Corrective actions include revising sampling heuristics, adding counter-examples, or adjusting LoRA regularization prompts.

## Reporting
- Bias metrics feed `artifacts/bias_reports/<timestamp>.json` for historical tracking.
- Weekly compliance bundles aggregate metrics across runs for governance review.

