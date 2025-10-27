#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="artifacts"
SBOM_PATH="${ARTIFACT_DIR}/sbom.json"
PREVIOUS="${ARTIFACT_DIR}/sbom_previous.json"

if [[ ! -f "${SBOM_PATH}" ]]; then
  bash scripts/generate_sbom.sh
fi

if [[ -f "${PREVIOUS}" ]]; then
  diff "${PREVIOUS}" "${SBOM_PATH}" || true
fi
cp "${SBOM_PATH}" "${PREVIOUS}"
