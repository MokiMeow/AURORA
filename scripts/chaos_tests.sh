#!/usr/bin/env bash
set -euo pipefail

echo "[chaos] Injecting sandbox failure scenarios"
python - <<'PY'
import random
scenarios = [
    "kill-planner",
    "drop-network",
    "corrupt-cache",
]
print("Simulated chaos scenario:", random.choice(scenarios))
PY

