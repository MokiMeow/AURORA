#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="artifacts"
REPORT="${ARTIFACT_DIR}/license_report.json"
mkdir -p "${ARTIFACT_DIR}"

if command -v pip-licenses >/dev/null 2>&1; then
  pip-licenses --format=json --output-file "${REPORT}"
else
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  cat <<EOF > "${REPORT}"
{
  "warning": "pip-licenses not installed",
  "generated_at": "${timestamp}",
  "packages": []
}
EOF
fi
