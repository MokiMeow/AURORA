#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${ROOT_DIR}/datasets"
SUITE="${1:-}"

case "${SUITE}" in
  swe-bench-lite)
    RUNNER="run.py"
    ;;
  swe-bench-live)
    RUNNER="run_live.py"
    ;;
  swe-bench-full)
    RUNNER="run_full.py"
    ;;
  *)
    echo "Usage: $0 {swe-bench-lite|swe-bench-live|swe-bench-full}" >&2
    exit 2
    ;;
esac

SUITE_DIR="${DATA_DIR}/${SUITE}"
RUNNER_PATH="${SUITE_DIR}/${RUNNER}"

if [[ ! -f "${RUNNER_PATH}" ]]; then
  echo "Evaluation data is not provisioned: expected ${RUNNER_PATH}" >&2
  echo "Place the licensed dataset and its runner in ${SUITE_DIR} before dispatching this workflow." >&2
  exit 2
fi

echo "Evaluation data ready at ${SUITE_DIR}"


