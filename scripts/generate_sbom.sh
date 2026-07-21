#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="artifacts"
SBOM_PATH="${ARTIFACT_DIR}/sbom.json"
mkdir -p "${ARTIFACT_DIR}"

if ! command -v cyclonedx-py >/dev/null 2>&1; then
  echo "cyclonedx-py is required; install the dev dependency group" >&2
  exit 2
fi

cyclonedx-py environment --output-format JSON --output-file "${SBOM_PATH}"
