# Governance Commands

- `aurora-se governance bundle --evaluation docs/governance/bundles/lite_latest.json`  
  Enriches the governance bundle with ethics charter, SLO summaries, alert rules, and SBOM/CVE artifacts.

- `aurora-se governance policy bundle.json`  
  Validates compliance thresholds (bias, SBOM presence) before release.

- `aurora-se governance report --weekly` / `--monthly`  
  Generates weekly dashboards or monthly compliance overviews.

- `aurora-se governance compliance`  
  Parses `configs/compliance/soc2_checklist.yaml`, reporting framework status counts for audits.

Use these commands in conjunction with telemetry exports and incident runbooks to maintain compliance readiness.
