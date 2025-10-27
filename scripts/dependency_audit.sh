#!/usr/bin/env bash
set -euo pipefail

poetry export --format requirements.txt > artifacts/requirements.txt
trivy fs --input artifacts/requirements.txt

