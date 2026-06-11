#!/bin/bash
set -euo pipefail

mkdir -p "${LOG_DIR:-/tmp/monitor}"
: > "${LOG_FILE:-/tmp/monitor/metrics.jsonl}"

echo "monitor-sidecar starting pod=${POD_NAME:-?} ns=${POD_NAMESPACE:-?} target=${TARGET_CONTAINER:-codehub} gpu=${GPU_ENABLED:-false}"

exec /app/collect.sh
