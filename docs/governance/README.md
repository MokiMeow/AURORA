# Governance Bundles

Evaluation runs publish governance bundles under `docs/governance/bundles/`.
Each bundle now includes:
- Evaluation compliance report with SBOM / CVE references.
- Planner / executor version metadata and SLO summary excerpts.
- Ethics charter and alert rules snapshot for auditors.
- Reward snapshot context for auditing.

Automation helpers live in `aurora/governance/automation.py`.

```
aurora-se governance bundle --evaluation docs/governance/bundles/lite_latest.json
```


