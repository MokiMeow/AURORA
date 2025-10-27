#!/usr/bin/env bash
set -euo pipefail

echo "[E2E] Running end-to-end dry run"
aurora-se init
aurora-se index --full
aurora-se plan --task "Dry run task" --auto
aurora-se apply --profile fast
aurora-se eval --suite swe-bench-lite --no-export-metrics

