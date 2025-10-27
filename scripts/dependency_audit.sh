#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="artifacts"
REPORT="${ARTIFACT_DIR}/dependency_audit.txt"
mkdir -p "${ARTIFACT_DIR}"

if command -v trivy >/dev/null 2>&1; then
  trivy fs --ignore-unfixed --severity HIGH,CRITICAL --output "${REPORT}" . || true
else
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "trivy not installed - ${timestamp}" > "${REPORT}"
fi
