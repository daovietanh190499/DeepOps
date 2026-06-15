#!/bin/bash
# Runtime control for port-tunnel (enabled via /config/sidecar/tunnel.json).
set -euo pipefail

CONFIG_FILE="${SIDECAR_CONFIG_FILE:-/config/sidecar/tunnel.json}"
OVERRIDE_FILE="${SIDECAR_OVERRIDE_FILE:-/tmp/sidecar/tunnel.json}"
WS_PORT="${WS_PORT:-8033}"
WS_PATH_PREFIX="${WS_PATH_PREFIX:-port-tunnel}"
TARGET_HOST="${TARGET_HOST:-127.0.0.1}"
WSTUNNEL_LOG="${WSTUNNEL_LOG:-info}"

WSTUNNEL_PID=""
ACTIVE=""
LAST_PORTS=""

stop_tunnel() {
  if [[ -n "${WSTUNNEL_PID}" ]] && kill -0 "${WSTUNNEL_PID}" 2>/dev/null; then
    kill "${WSTUNNEL_PID}" 2>/dev/null || true
    wait "${WSTUNNEL_PID}" 2>/dev/null || true
  fi
  WSTUNNEL_PID=""
  ACTIVE=""
}

start_tunnel() {
  local ports_csv="$1"
  stop_tunnel

  local args=(wstunnel server --log-lvl "${WSTUNNEL_LOG}" -r "${WS_PATH_PREFIX}")
  IFS=','
  for port in ${ports_csv}; do
    port="${port// /}"
    [[ -n "${port}" ]] || continue
    args+=(--restrict-to "${TARGET_HOST}:${port}")
  done
  unset IFS
  args+=("ws://[::]:${WS_PORT}")

  "${args[@]}" &
  WSTUNNEL_PID=$!
  ACTIVE=1
  LAST_PORTS="${ports_csv}"
  echo "port-tunnel: active ports=${ports_csv}"
}

config_file() {
  if [[ -f "${OVERRIDE_FILE}" ]]; then
    echo "${OVERRIDE_FILE}"
  else
    echo "${CONFIG_FILE}"
  fi
}

apply_config() {
  local enabled="false"
  local ports=""
  local file
  file="$(config_file)"
  if [[ -f "${file}" ]]; then
    enabled="$(jq -r '.enabled // false' "${file}")"
    ports="$(jq -r '(.ports // []) | map(tostring) | join(",")' "${file}")"
  fi

  if [[ "${enabled}" == "true" ]] && [[ -n "${ports// /}" ]]; then
    if [[ "${ACTIVE}" == "1" ]] && kill -0 "${WSTUNNEL_PID}" 2>/dev/null && [[ "${ports}" == "${LAST_PORTS}" ]]; then
      return
    fi
    start_tunnel "${ports}" || true
  else
    LAST_PORTS=""
    if [[ "${ACTIVE}" == "1" ]]; then
      stop_tunnel
      echo "port-tunnel: idle"
    fi
  fi
}

trap 'stop_tunnel; exit 0' TERM INT
trap 'apply_config' HUP

echo "port-tunnel supervisor watching ${CONFIG_FILE}"
apply_config

while true; do
  sleep 3
  apply_config
done
