# Compliance & Governance Summary (Phase 8)

- **Frameworks Tracked**: SOC2 Type II, ISO 27001 control mappings.
- **Checklist Source**: `configs/compliance/soc2_checklist.yaml`
- **Automation Coverage**:
  - Checklist parsing and status reporting via `aurora-se governance compliance`.
  - Governance bundle enrichment with ethics charter, SLO summaries, alert rules, SBOM/CVE status.
  - Telemetry export metadata captures interval, environment, and retention context.
- **Stakeholder Reviews**:
  - Governance committee reviewed bundle on each release candidate.
  - Incident commander confirms runbook updates post tabletop exercises.
- **Next Actions**:
  - Finish ISO 27001 annex control mapping.
  - Automate evidence collection for change management approvals.
