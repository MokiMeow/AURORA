# Governance Bundle Procedures

## Daily Tasks
- Review latest bundle in `docs/governance/bundles/`.
- Verify compliance issues array is empty; escalate if not.
- Check reward snapshot aligns with policy thresholds.

## Weekly Tasks
- Run `aurora-se eval --suite swe-bench-lite` to refresh metrics.
- Execute `aurora-se governance bundle` (placeholder) to regenerate report.
- Inspect `docs/reports/weekly_dashboard.html` and `weekly_governance.md` for anomalies.

## Incident Response
- Log overrides via governance CLI policy command (future enhancement).
- Attach evidence to compliance bundle template (`docs/governance/compliance_bundle_template.md`).

