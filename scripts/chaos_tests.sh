#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="artifacts"
REPORT="${ARTIFACT_DIR}/chaos_report.json"
mkdir -p "${ARTIFACT_DIR}"

echo "[chaos] Injecting sandbox failure scenarios"
python - <<'PY'
import json
import random
from datetime import datetime

scenarios = [
    "kill-planner",
    "drop-network",
    "corrupt-cache",
    "firecracker-sigterm",
    "cpu-throttle",
]
choice = random.choice(scenarios)
report = {
    "scenario": choice,
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "status": "simulated",
}
print(json.dumps(report))
PY > "${REPORT}"

