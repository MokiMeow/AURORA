# Incident Response Runbook (Phase 8)

1. **Detect**  
   - Telemetry alerts `CompliancePolicyViolation` or `TelemetryIngestionStall` fire via Prometheus/Alertmanager.
   - Pager policy: `opsgenie-critical`.

2. **Triage**  
   - Acknowledge alert within 5 minutes.  
   - Review telemetry export (`aurora-se telemetry export --interval 1h`) for correlated errors.
   - Confirm governance bundle status and policy overrides.

3. **Contain**  
   - Pause autopilot executions (`aurora-se api stop`) if the incident is deployment-related.
   - Disable affected plugins using `/plugin disable` inside the shell.

4. **Eradicate**  
   - Apply remediation diff via executor with manual approval.
   - Commit SBOM/CVE fixes; rerun policy checks.

5. **Recover**  
   - Re-enable services; monitor dashboards using `aurora-se telemetry dashboard --remote`.
   - Ensure reward/telemetry metrics return to steady state.

6. **Post-Incident Review**  
   - Update `configs/compliance/soc2_checklist.yaml` status.
   - Capture lessons in `docs/governance/compliance_summary.md`.
