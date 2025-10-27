#!/usr/bin/env bash
set -euo pipefail

pip-licenses --format=json --output-file artifacts/licenses.json

