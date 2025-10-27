#!/usr/bin/env bash
set -euo pipefail

syft dir:. -o json > artifacts/sbom_current.json
if [[ -f artifacts/sbom_previous.json ]]; then
  diff artifacts/sbom_previous.json artifacts/sbom_current.json || true
fi
cp artifacts/sbom_current.json artifacts/sbom_previous.json

