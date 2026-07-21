#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="artifacts"
REPORT="${ARTIFACT_DIR}/license_report.json"
mkdir -p "${ARTIFACT_DIR}"

if ! command -v pip-licenses >/dev/null 2>&1; then
  echo "pip-licenses is required; install the dev dependency group" >&2
  exit 2
fi

pip-licenses --format=json --output-file "${REPORT}"
