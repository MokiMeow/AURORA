#!/usr/bin/env bash
set -euo pipefail

grype dir:. --fail-on critical

