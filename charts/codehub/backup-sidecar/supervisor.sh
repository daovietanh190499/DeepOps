#!/bin/bash
# Runtime control for backup-sidecar (start/stop/reload via hub API → ConfigMap).
set -euo pipefail

LOG_DIR="${LOG_DIR:-/tmp/backup}"
STATUS_FILE="${STATUS_FILE:-${LOG_DIR}/status.json}"
RCLONE_CONFIG="${RCLONE_CONFIG:-/config/rclone.conf}"
CONFIG_FILE="${SIDECAR_CONFIG_FILE:-/config/sidecar/backup.json}"
CRON_PID=""
LAST_CONFIG_HASH=""

mkdir -p "${LOG_DIR}"

init_status() {
  if [[ ! -f "${STATUS_FILE}" ]]; then
    jq -n \
      --arg last_run_at "" \
      --argjson last_success null \
      --arg last_message "Backup idle" \
      --argjson running false \
      --arg trigger "" \
      '{
        last_run_at: $last_run_at,
        last_success: $last_success,
        last_message: $last_message,
        running: $running,
        trigger: $trigger
      }' > "${STATUS_FILE}"
  fi
}

stop_cron() {
  if [[ -n "${CRON_PID}" ]] && kill -0 "${CRON_PID}" 2>/dev/null; then
    kill "${CRON_PID}" 2>/dev/null || true
    wait "${CRON_PID}" 2>/dev/null || true
  fi
  CRON_PID=""
  crontab -r 2>/dev/null || true
}

start_cron() {
  local schedule="$1"
  local remote="$2"
  local folders="$3"
  local cron_file="/tmp/backup-crontab"

  stop_cron

  {
    echo "SHELL=/bin/bash"
    echo "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    echo "BACKUP_REMOTE=${remote}"
    echo "BACKUP_FOLDERS=${folders}"
    echo "BACKUP_SCHEDULE=${schedule}"
    echo "LOG_DIR=${LOG_DIR}"
    echo "RCLONE_CONFIG=${RCLONE_CONFIG}"
    echo "STATUS_FILE=${STATUS_FILE}"
    echo "${schedule} /app/run-backup.sh cron >> ${LOG_DIR}/cron.log 2>&1"
  } > "${cron_file}"
  crontab "${cron_file}"

  cron -f &
  CRON_PID=$!
  echo "backup-sidecar: cron active (${schedule}) remote=${remote} folders=${folders}"
}

apply_config() {
  if [[ ! -f "${CONFIG_FILE}" ]]; then
    stop_cron
    LAST_CONFIG_HASH=""
    return
  fi

  local config_hash
  config_hash="$(md5sum "${CONFIG_FILE}" | awk '{print $1}')"
  if [[ "${config_hash}" == "${LAST_CONFIG_HASH}" ]] \
      && [[ -n "${CRON_PID}" ]] && kill -0 "${CRON_PID}" 2>/dev/null; then
    return
  fi
  LAST_CONFIG_HASH="${config_hash}"

  local enabled schedule remote folders
  enabled="$(jq -r '.enabled // false' "${CONFIG_FILE}")"
  schedule="$(jq -r '.schedule // ""' "${CONFIG_FILE}")"
  remote="$(jq -r '.remote // ""' "${CONFIG_FILE}")"
  folders="$(jq -c '.folders // []' "${CONFIG_FILE}")"

  if [[ "${enabled}" != "true" ]] || [[ -z "${schedule}" ]] || [[ -z "${remote}" ]]; then
    stop_cron
    LAST_CONFIG_HASH="${config_hash}"
    jq '.last_message = "Backup idle"' "${STATUS_FILE}" > "${STATUS_FILE}.tmp" 2>/dev/null \
      && mv "${STATUS_FILE}.tmp" "${STATUS_FILE}" || true
    echo "backup-sidecar: idle"
    return
  fi

  if [[ ! -f "${RCLONE_CONFIG}" ]]; then
    echo "backup-sidecar: waiting for rclone config at ${RCLONE_CONFIG}"
    stop_cron
    return
  fi

  start_cron "${schedule}" "${remote}" "${folders}"
}

trap 'stop_cron; exit 0' TERM INT
trap 'apply_config' HUP

init_status
echo "backup-sidecar supervisor watching ${CONFIG_FILE}"
apply_config

while true; do
  sleep 3
  apply_config
done
