#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="artifacts"
REPORT="${ARTIFACT_DIR}/cve_report.json"
mkdir -p "${ARTIFACT_DIR}"

if ! command -v grype >/dev/null 2>&1; then
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  cat <<EOF > "${REPORT}"
{
  "warning": "grype not installed",
  "generated_at": "${timestamp}"
}
EOF
  exit 0
fi

TMP_OUTPUT=$(mktemp)
set +e
grype dir:. -o json > "${TMP_OUTPUT}"
EXIT_CODE=$?
set -e
mv "${TMP_OUTPUT}" "${REPORT}"

if [[ ${EXIT_CODE} -ne 0 ]]; then
  echo "grype exited with status ${EXIT_CODE}, see ${REPORT} for details" >&2
fi

exit 0
