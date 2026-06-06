#!/bin/bash
set -euo pipefail

WS_PORT="${WS_PORT:-8022}"
WS_PATH_PREFIX="${WS_PATH_PREFIX:-ssh-tunnel}"
SSH_PORT="${SSH_PORT:-2222}"
WSTUNNEL_LOG="${WSTUNNEL_LOG:-info}"

python /app/server.py &
ssh_pid=$!

cleanup() {
  kill "$ssh_pid" 2>/dev/null || true
}
trap cleanup EXIT

ready=0
for i in $(seq 1 50); do
  if ! kill -0 "$ssh_pid" 2>/dev/null; then
    echo "asyncssh server exited before binding port ${SSH_PORT}" >&2
    wait "$ssh_pid" || true
    exit 1
  fi
  if (echo >/dev/tcp/127.0.0.1/"${SSH_PORT}") 2>/dev/null; then
    ready=1
    echo "asyncssh ready on 127.0.0.1:${SSH_PORT}"
    break
  fi
  sleep 0.2
done

if [ "$ready" -ne 1 ]; then
  echo "timeout waiting for asyncssh on 127.0.0.1:${SSH_PORT}" >&2
  kill "$ssh_pid" 2>/dev/null || true
  wait "$ssh_pid" || true
  exit 1
fi

echo "starting wstunnel server on :${WS_PORT} path-prefix=${WS_PATH_PREFIX} -> 127.0.0.1:${SSH_PORT}"
exec wstunnel server \
  --log-lvl "${WSTUNNEL_LOG}" \
  --restrict-to "127.0.0.1:${SSH_PORT}" \
  -r "${WS_PATH_PREFIX}" \
  "ws://[::]:${WS_PORT}"
