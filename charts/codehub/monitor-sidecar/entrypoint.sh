#!/bin/bash
set -euo pipefail

mkdir -p "${LOG_DIR:-/tmp/monitor}"
echo "monitor-sidecar starting pod=${POD_NAME:-?} ns=${POD_NAMESPACE:-?} target=${TARGET_CONTAINER:-codehub} gpu=${GPU_ENABLED:-false}"

exec /app/supervisor.sh
