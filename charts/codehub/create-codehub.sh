#!/usr/bin/env bash
# Example: spawn codehub with DirectPV
set -euo pipefail

export USERNAME="${USERNAME:-exampleuser}"
export PASSWORD="${PASSWORD:-changeme}"
export CPU="${CPU:-2}"
export RAM="${RAM:-4G}"
export GPU="${GPU:-none}"
export VOLUME_SIZE="${VOLUME_SIZE:-20Gi}"
export STORAGE_CLASS="${STORAGE_CLASS:-directpv-min-io}"
export NAMESPACE="${NAMESPACE:-dohub}"
export DOMAIN_NAME="${DOMAIN_NAME:-dohub.com}"
export CODEHUB_CHART_PATH="${CODEHUB_CHART_PATH:-$(cd "$(dirname "$0")" && pwd)}"

"$(dirname "$0")/../jenkins/scripts/codehub-spawn.sh"
