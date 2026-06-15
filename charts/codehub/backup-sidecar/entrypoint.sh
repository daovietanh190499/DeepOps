#!/bin/bash
set -euo pipefail

LOG_DIR="${LOG_DIR:-/tmp/backup}"
STATUS_FILE="${STATUS_FILE:-${LOG_DIR}/status.json}"
RCLONE_CONFIG="${RCLONE_CONFIG:-/config/rclone.conf}"

mkdir -p "${LOG_DIR}"

if [[ ! -f "${RCLONE_CONFIG}" ]]; then
  echo "backup-sidecar: waiting for rclone config at ${RCLONE_CONFIG}"
fi

SCHEDULE="${BACKUP_SCHEDULE:-}"
if [[ -n "${SCHEDULE}" ]]; then
  CRON_FILE="/tmp/backup-crontab"
  {
    echo "SHELL=/bin/bash"
    echo "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    # cron jobs do not inherit the container environment — export backup settings here
    echo "BACKUP_REMOTE=${BACKUP_REMOTE:-}"
    echo "BACKUP_FOLDERS=${BACKUP_FOLDERS:-[]}"
    echo "BACKUP_SCHEDULE=${SCHEDULE}"
    echo "LOG_DIR=${LOG_DIR}"
    echo "RCLONE_CONFIG=${RCLONE_CONFIG}"
    echo "STATUS_FILE=${STATUS_FILE}"
    echo "${SCHEDULE} /app/run-backup.sh cron >> ${LOG_DIR}/cron.log 2>&1"
  } > "${CRON_FILE}"
  crontab "${CRON_FILE}"
  echo "backup-sidecar: cron scheduled (${SCHEDULE})"
else
  crontab -r 2>/dev/null || true
  echo "backup-sidecar: no cron schedule configured"
fi

if [[ ! -f "${STATUS_FILE}" ]]; then
  jq -n \
    --arg last_run_at "" \
    --argjson last_success null \
    --arg last_message "No backup run yet" \
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

echo "backup-sidecar starting remote=${BACKUP_REMOTE:-?} folders=${BACKUP_FOLDERS:-[]}"
exec cron -f
