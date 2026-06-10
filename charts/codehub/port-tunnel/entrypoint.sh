#!/bin/bash
set -euo pipefail

WS_PORT="${WS_PORT:-8033}"
WS_PATH_PREFIX="${WS_PATH_PREFIX:-port-tunnel}"
TARGET_HOST="${TARGET_HOST:-127.0.0.1}"
TUNNEL_PORTS="${TUNNEL_PORTS:-}"
WSTUNNEL_LOG="${WSTUNNEL_LOG:-info}"

if [ -z "${TUNNEL_PORTS// /}" ]; then
  echo "TUNNEL_PORTS is empty — nothing to expose" >&2
  exit 1
fi

args=(wstunnel server --log-lvl "${WSTUNNEL_LOG}" -r "${WS_PATH_PREFIX}")
IFS=','
for port in ${TUNNEL_PORTS}; do
  port="${port// /}"
  [ -n "${port}" ] || continue
  args+=(--restrict-to "${TARGET_HOST}:${port}")
done
args+=("ws://[::]:${WS_PORT}")

echo "starting wstunnel port server path-prefix=${WS_PATH_PREFIX} ports=${TUNNEL_PORTS} -> ${TARGET_HOST}"
exec "${args[@]}"
