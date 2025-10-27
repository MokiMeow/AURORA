#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="artifacts"
SBOM_PATH="${ARTIFACT_DIR}/sbom.json"
mkdir -p "${ARTIFACT_DIR}"

if command -v syft >/dev/null 2>&1; then
  syft dir:. -o json > "${SBOM_PATH}"
else
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  cat <<EOF > "${SBOM_PATH}"
{
  "warning": "syft not installed",
  "generated_at": "${timestamp}"
}
EOF
fi
