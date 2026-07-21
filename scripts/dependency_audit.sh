#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="artifacts"
REPORT="${ARTIFACT_DIR}/dependency_audit.json"
mkdir -p "${ARTIFACT_DIR}"

if ! command -v pip-audit >/dev/null 2>&1; then
  echo "pip-audit is required; install the dev dependency group" >&2
  exit 2
fi

pip-audit --format json --output "${REPORT}"
