# Telemetry Alert Playbook

## PDCA Error Spike (Warning)
1. Navigate to Grafana dashboard (`aurora-se telemetry dashboard --remote`).
2. Filter on affected tenant and timeframe.
3. Review reward history (`artifacts/reward_reports/latest_reward.json`) for regressions.
4. Trigger `aurora-se governance bundle --sbom artifacts/sbom/latest.json` if policy impact suspected.

## Telemetry Ingestion Stall (Critical)
1. Check OTEL collector logs using `aurora-se telemetry export --interval 15m`.
2. Validate collector configuration matches environment (`configs/telemetry/<env>.yaml`).
3. Recycle collector deployment or fallback to local collector (`configs/telemetry/collector.local.yaml`).
4. Resume ingestion and monitor message rates for 30 minutes.

## Compliance Policy Violation (Critical)
1. Generate compliance report via `aurora-se governance compliance`.
2. Engage governance lead for approval decisions.
3. Update incident response ticket with remediation plan and timeline.
