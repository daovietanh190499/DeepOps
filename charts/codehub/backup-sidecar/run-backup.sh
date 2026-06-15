#!/bin/bash
set -euo pipefail

LOG_DIR="${LOG_DIR:-/tmp/backup}"
STATUS_FILE="${STATUS_FILE:-${LOG_DIR}/status.json}"
LOCK_FILE="${LOCK_FILE:-${LOG_DIR}/backup.lock}"
RCLONE_CONFIG="${RCLONE_CONFIG:-/config/rclone.conf}"
BACKUP_REMOTE="${BACKUP_REMOTE:-}"
TRIGGER="${1:-cron}"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

mkdir -p "${LOG_DIR}"

write_status() {
  local running="$1"
  local success="$2"
  local message="$3"
  local run_at="$4"
  if [[ "${success}" == "null" ]]; then
    jq -n \
      --arg last_run_at "${run_at}" \
      --arg last_message "${message}" \
      --argjson running "${running}" \
      --arg trigger "${TRIGGER}" \
      '{
        last_run_at: $last_run_at,
        last_success: null,
        last_message: $last_message,
        running: $running,
        trigger: $trigger
      }' > "${STATUS_FILE}"
  else
    jq -n \
      --arg last_run_at "${run_at}" \
      --argjson last_success "${success}" \
      --arg last_message "${message}" \
      --argjson running "${running}" \
      --arg trigger "${TRIGGER}" \
      '{
        last_run_at: $last_run_at,
        last_success: $last_success,
        last_message: $last_message,
        running: $running,
        trigger: $trigger
      }' > "${STATUS_FILE}"
  fi
}

remote_suffix() {
  local folder="$1"
  local trimmed="${folder#/}"
  trimmed="${trimmed%/}"
  if [[ -z "${trimmed}" ]]; then
    echo "root"
    return
  fi
  echo "${trimmed}" | tr '/' '_'
}

if [[ ! -f "${RCLONE_CONFIG}" ]]; then
  write_status false false "rclone config missing at ${RCLONE_CONFIG}" "${TS}"
  exit 1
fi

if [[ -z "${BACKUP_REMOTE}" ]]; then
  write_status false false "BACKUP_REMOTE is not set" "${TS}"
  exit 1
fi

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  write_status true null "Backup already running" "${TS}"
  exit 0
fi

if [[ -f "${STATUS_FILE}" ]] && jq -e '.running == true' "${STATUS_FILE}" >/dev/null 2>&1; then
  write_status false null "Recovered from interrupted backup" "${TS}"
fi

write_status true null "Running…" "${TS}"

LOG_FILE="${LOG_DIR}/backup-${TS//:/-}.log"
: > "${LOG_FILE}"

FOLDERS=()
if [[ "${BACKUP_FOLDERS}" == \[* ]]; then
  mapfile -t FOLDERS < <(printf '%s' "${BACKUP_FOLDERS}" | jq -r '.[]? // empty')
else
  IFS=',' read -ra FOLDERS <<< "${BACKUP_FOLDERS}"
fi

if [[ ${#FOLDERS[@]} -eq 0 ]]; then
  write_status false false "No backup folders configured" "${TS}"
  exit 1
fi

overall_ok=true
messages=()

for folder in "${FOLDERS[@]}"; do
  folder="$(printf '%s' "${folder}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -n "${folder}" ]] || continue
  if [[ ! -d "${folder}" ]]; then
    overall_ok=false
    messages+=("missing folder: ${folder}")
    continue
  fi
  suffix="$(remote_suffix "${folder}")"
  dest="${BACKUP_REMOTE%/}/${suffix}"
  echo "[${TS}] rclone sync ${folder} -> ${dest}" >> "${LOG_FILE}"
  if rclone sync "${folder}" "${dest}" \
      --config "${RCLONE_CONFIG}" \
      --log-file "${LOG_FILE}" \
      --log-level INFO \
      --stats 30s; then
    messages+=("ok: ${folder}")
  else
    overall_ok=false
    messages+=("failed: ${folder}")
  fi
done

MSG="$(IFS='; '; echo "${messages[*]}")"
if [[ "${overall_ok}" == true ]]; then
  write_status false true "${MSG}" "${TS}"
else
  write_status false false "${MSG}" "${TS}"
fi

ln -sf "${LOG_FILE}" "${LOG_DIR}/latest.log"
