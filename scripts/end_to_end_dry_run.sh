#!/usr/bin/env bash
set -euo pipefail

echo "[E2E] Running end-to-end dry run"
aurora-se init
aurora-se index --full
aurora-se autopilot --task "Dry run task" --dry-run --max-iterations 2


