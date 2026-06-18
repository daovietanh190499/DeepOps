#!/bin/bash
# Runtime control for ssh-bridge (enabled via /config/sidecar/ssh.json).
set -euo pipefail

CONFIG_FILE="${SIDECAR_CONFIG_FILE:-/config/sidecar/ssh.json}"
WS_PORT="${WS_PORT:-8022}"
WS_PATH_PREFIX="${WS_PATH_PREFIX:-ssh-tunnel}"
SSH_PORT="${SSH_PORT:-2222}"
WSTUNNEL_LOG="${WSTUNNEL_LOG:-info}"
AUTHORIZED_KEYS="${AUTHORIZED_KEYS:-/ssh-secrets/authorized_keys}"
HOST_KEY="${HOST_KEY:-/ssh-secrets/host_key}"
RUNTIME_AUTH="/tmp/sidecar/ssh/authorized_keys"
RUNTIME_HOST="/tmp/sidecar/ssh/host_key"

SSH_PID=""
WSTUNNEL_PID=""
ACTIVE=""
RUNNING_SHELL=""
RUNNING_KEYS_FP=""

stop_stack() {
  if [[ -n "${WSTUNNEL_PID}" ]] && kill -0 "${WSTUNNEL_PID}" 2>/dev/null; then
    kill "${WSTUNNEL_PID}" 2>/dev/null || true
    wait "${WSTUNNEL_PID}" 2>/dev/null || true
  fi
  if [[ -n "${SSH_PID}" ]] && kill -0 "${SSH_PID}" 2>/dev/null; then
    kill "${SSH_PID}" 2>/dev/null || true
    wait "${SSH_PID}" 2>/dev/null || true
  fi
  WSTUNNEL_PID=""
  SSH_PID=""
  ACTIVE=""
  RUNNING_SHELL=""
}

_effective_auth_keys() {
  if [[ -f "${RUNTIME_AUTH}" ]]; then
    echo "${RUNTIME_AUTH}"
  else
    echo "${AUTHORIZED_KEYS}"
  fi
}

_effective_host_key() {
  if [[ -f "${RUNTIME_HOST}" ]]; then
    echo "${RUNTIME_HOST}"
  else
    echo "${HOST_KEY}"
  fi
}

_keys_fingerprint() {
  local ak hk
  ak="$(_effective_auth_keys)"
  hk="$(_effective_host_key)"
  if [[ -f "${ak}" && -f "${hk}" ]]; then
    md5sum "${ak}" "${hk}" 2>/dev/null | md5sum | awk '{print $1}'
  fi
}

keys_ready() {
  local ak hk
  ak="$(_effective_auth_keys)"
  hk="$(_effective_host_key)"
  [[ -f "${ak}" ]] || return 1
  [[ -f "${hk}" ]] || return 1
  grep -qE '^(ssh-ed25519|ssh-rsa|ecdsa-sha2-)' "${ak}" || return 1
  grep -q 'BEGIN OPENSSH PRIVATE KEY' "${hk}" || return 1
  return 0
}

start_stack() {
  stop_stack
  export EXEC_SHELL="${DESIRED_SHELL:-bash}"
  export AUTHORIZED_KEYS="$(_effective_auth_keys)"
  export HOST_KEY="$(_effective_host_key)"
  python /app/server.py &
  SSH_PID=$!

  local ready=0
  for _ in $(seq 1 50); do
    if ! kill -0 "${SSH_PID}" 2>/dev/null; then
      wait "${SSH_PID}" || true
      echo "asyncssh server exited before binding port ${SSH_PORT}" >&2
      SSH_PID=""
      return 1
    fi
    if (echo >/dev/tcp/127.0.0.1/"${SSH_PORT}") 2>/dev/null; then
      ready=1
      break
    fi
    sleep 0.2
  done

  if [[ "${ready}" -ne 1 ]]; then
    echo "timeout waiting for asyncssh on 127.0.0.1:${SSH_PORT}" >&2
    stop_stack
    return 1
  fi

  wstunnel server \
    --log-lvl "${WSTUNNEL_LOG}" \
    --restrict-to "127.0.0.1:${SSH_PORT}" \
    -r "${WS_PATH_PREFIX}" \
    "ws://[::]:${WS_PORT}" &
  WSTUNNEL_PID=$!
  ACTIVE=1
  RUNNING_SHELL="${EXEC_SHELL}"
  RUNNING_KEYS_FP="$(_keys_fingerprint)"
  echo "ssh-bridge: active on ws :${WS_PORT} (shell=${EXEC_SHELL})"
}

apply_config() {
  local enabled="false"
  DESIRED_SHELL="bash"
  if [[ -f "${CONFIG_FILE}" ]]; then
    enabled="$(jq -r '.enabled // false' "${CONFIG_FILE}")"
    DESIRED_SHELL="$(jq -r '.exec_shell // "bash"' "${CONFIG_FILE}")"
  fi
  case "${DESIRED_SHELL}" in
    bash|sh) ;;
    *) DESIRED_SHELL="bash" ;;
  esac

  if [[ "${enabled}" == "true" ]] && keys_ready; then
    local fp
    fp="$(_keys_fingerprint)"
    if [[ "${ACTIVE}" != "1" ]]; then
      start_stack || true
    elif [[ "${RUNNING_SHELL}" != "${DESIRED_SHELL}" ]]; then
      start_stack || true
    elif [[ -n "${fp}" && "${fp}" != "${RUNNING_KEYS_FP}" ]]; then
      echo "ssh-bridge: keys changed, restarting stack"
      start_stack || true
    elif ! kill -0 "${SSH_PID}" 2>/dev/null || ! kill -0 "${WSTUNNEL_PID}" 2>/dev/null; then
      start_stack || true
    fi
  else
    if [[ "${ACTIVE}" == "1" ]]; then
      stop_stack
      RUNNING_KEYS_FP=""
      echo "ssh-bridge: idle"
    fi
  fi
}

trap 'stop_stack; exit 0' TERM INT
trap 'apply_config' HUP

echo "ssh-bridge supervisor watching ${CONFIG_FILE}"
apply_config

while true; do
  sleep 3
  apply_config
done
