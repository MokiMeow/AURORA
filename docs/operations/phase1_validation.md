# Phase 1 Validation Log

Date: $(Get-Date -Format s)Z

## Executed Checks

| Check | Command | Result |
|-------|---------|--------|
| Docker sandbox smoke | `pytest tests/test_executor_sandbox.py -k docker` | pass |
| Firecracker sandbox smoke (simulated) | `pytest tests/test_executor_sandbox.py -k firecracker` | pass (no firectl on host; asserts graceful error path) |
| Secret scanner integration | `pytest tests/test_security_secrets.py` | pass |
| Policy enforcement | `pytest tests/test_executor_policy.py` | pass |
| SBOM generation | `bash scripts/generate_sbom.sh` | fallback (no syft on host, warning JSON written via artifact helper) |
| CVE scan | `bash scripts/grype_scan.sh` | fallback (no grype on host, warning JSON written via artifact helper) |
| License report | `bash scripts/license_check.sh` | fallback (pip-licenses unavailable, warning JSON written) |
| Dependency audit | `bash scripts/dependency_audit.sh` | fallback (trivy unavailable, warning text written) |
| Chaos scenario | `bash scripts/chaos_tests.sh` | simulated run logged to `artifacts/chaos_report.json` |

## Artifacts

- `artifacts/sbom.json`
- `artifacts/cve_report.json`
- `artifacts/license_report.json`
- `artifacts/dependency_audit.txt`
- `artifacts/chaos_report.json`

## Notes

- Container and microVM sandboxes are validated through unit tests; full microVM launch is simulated due to missing `firectl` binary on this workstation. CI runners provide the required toolchain.
- SBOM/CVE/license scripts are wired into CI; local execution used scripted fallbacks because Syft/Grype/Pip-Licenses are not installed in this environment.
- Chaos harness emits JSON describing the simulated failure mode which is ingested by governance telemetry.
