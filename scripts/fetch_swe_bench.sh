#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${ROOT_DIR}/datasets"

mkdir -p "${DATA_DIR}"/swe-bench-{lite,live,full}

echo "[fetch] syncing SWE-Bench datasets (placeholders)"
touch "${DATA_DIR}/swe-bench-lite/README.md"
touch "${DATA_DIR}/swe-bench-live/README.md"
touch "${DATA_DIR}/swe-bench-full/README.md"

echo "Datasets prepared under ${DATA_DIR}"

