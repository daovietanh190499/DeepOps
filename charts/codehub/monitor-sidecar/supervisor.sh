#!/bin/bash
# Runtime control for monitor-sidecar (enabled via /config/sidecar/monitor.json).
set -euo pipefail

CONFIG_FILE="${SIDECAR_CONFIG_FILE:-/config/sidecar/monitor.json}"
COLLECT_PID=""
ACTIVE=""

stop_collect() {
  if [[ -n "${COLLECT_PID}" ]] && kill -0 "${COLLECT_PID}" 2>/dev/null; then
    kill "${COLLECT_PID}" 2>/dev/null || true
    wait "${COLLECT_PID}" 2>/dev/null || true
  fi
  COLLECT_PID=""
  ACTIVE=""
}

start_collect() {
  stop_collect
  /app/collect.sh &
  COLLECT_PID=$!
  ACTIVE=1
  echo "monitor-sidecar: active"
}

apply_config() {
  local enabled="true"
  if [[ -f "${CONFIG_FILE}" ]]; then
    enabled="$(jq -r '.enabled // true' "${CONFIG_FILE}")"
  fi

  if [[ "${enabled}" == "true" ]]; then
    if [[ "${ACTIVE}" != "1" ]]; then
      start_collect
    elif ! kill -0 "${COLLECT_PID}" 2>/dev/null; then
      start_collect
    fi
  else
    if [[ "${ACTIVE}" == "1" ]]; then
      stop_collect
      echo "monitor-sidecar: idle"
    fi
  fi
}

trap 'stop_collect; exit 0' TERM INT
trap 'apply_config' HUP

mkdir -p "${LOG_DIR:-/tmp/monitor}"
echo "monitor-sidecar supervisor watching ${CONFIG_FILE}"
apply_config

while true; do
  sleep 3
  apply_config
done
