#!/bin/bash
set -euo pipefail

LOG_DIR="${LOG_DIR:-/tmp/monitor}"
INTERVAL_SEC="${INTERVAL_SEC:-2}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TARGET_CONTAINER="${TARGET_CONTAINER:-codehub}"
GPU_ENABLED="${GPU_ENABLED:-false}"
CPU_LIMIT_MILLICORES="${CPU_LIMIT_MILLICORES:-2000}"
MEMORY_LIMIT_BYTES="${MEMORY_LIMIT_BYTES:-4294967296}"

CURRENT_DAY=""

mkdir -p "$LOG_DIR"

parse_cpu_to_millicores() {
  local raw="${1:-0}"
  raw="${raw// /}"
  if [[ "$raw" == *m ]]; then
    echo "${raw%m}"
    return
  fi
  if [[ "$raw" == *.* ]]; then
    awk -v v="$raw" 'BEGIN { printf "%.0f", v * 1000 }'
    return
  fi
  echo $(( raw * 1000 ))
}

parse_mem_to_bytes() {
  local raw="${1:-0}"
  raw="${raw// /}"
  if [[ "$raw" == *Ki ]]; then
    echo $(( ${raw%Ki} * 1024 ))
  elif [[ "$raw" == *Mi ]]; then
    echo $(( ${raw%Mi} * 1024 * 1024 ))
  elif [[ "$raw" == *Gi ]]; then
    echo $(( ${raw%Gi} * 1024 * 1024 * 1024 ))
  elif [[ "$raw" == *Ti ]]; then
    echo $(( ${raw%Ti} * 1024 * 1024 * 1024 * 1024 ))
  elif [[ "$raw" =~ ^[0-9]+$ ]]; then
    echo "$raw"
  else
    echo 0
  fi
}

daily_log_file() {
  echo "${LOG_DIR}/metrics-$(date -u +%Y-%m-%d).jsonl"
}

purge_old_logs() {
  local retention_days="${RETENTION_DAYS:-30}"
  local cutoff_day
  cutoff_day=$(date -u -d "${retention_days} days ago" +%Y-%m-%d)

  local f base day
  for f in "$LOG_DIR"/metrics-*.jsonl; do
    [[ -e "$f" ]] || continue
    base="${f##*/}"
    day="${base#metrics-}"
    day="${day%.jsonl}"
    if [[ "$day" < "$cutoff_day" ]]; then
      rm -f "$f"
    fi
  done

  # Drop legacy single-file format if present (rm -f avoids set -e exit when missing).
  rm -f "$LOG_DIR/metrics.jsonl"
}

collect_once() {
  local today log_file ts cpu_raw mem_raw cpu_m mem_b gpu_util gpu_mem_used gpu_mem_total

  today=$(date -u +%Y-%m-%d)
  if [[ "$today" != "$CURRENT_DAY" ]]; then
    CURRENT_DAY="$today"
    purge_old_logs
  fi

  log_file=$(daily_log_file)
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  cpu_raw=""
  mem_raw=""
  if [[ -n "${POD_NAME:-}" && -n "${POD_NAMESPACE:-}" ]]; then
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      local pod_name ctr_name
      pod_name=$(echo "$line" | awk '{print $1}')
      ctr_name=$(echo "$line" | awk '{print $2}')
      if [[ "$pod_name" == "$POD_NAME" && "$ctr_name" == "$TARGET_CONTAINER" ]]; then
        cpu_raw=$(echo "$line" | awk '{print $3}')
        mem_raw=$(echo "$line" | awk '{print $4}')
        break
      fi
    done < <(kubectl top pod -n "$POD_NAMESPACE" --containers --no-headers 2>/dev/null || true)
  fi

  cpu_m=$(parse_cpu_to_millicores "${cpu_raw:-0}")
  mem_b=$(parse_mem_to_bytes "${mem_raw:-0}")

  gpu_util="null"
  gpu_mem_used="null"
  gpu_mem_total="null"
  if [[ "${GPU_ENABLED}" == "true" && -n "${POD_NAME:-}" && -n "${POD_NAMESPACE:-}" ]]; then
    local gpu_line
    gpu_line=$(kubectl exec "$POD_NAME" -n "$POD_NAMESPACE" -c "$TARGET_CONTAINER" -- \
      nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total \
      --format=csv,noheader,nounits 2>/dev/null | head -1 || true)
    if [[ -n "$gpu_line" ]]; then
      gpu_util=$(echo "$gpu_line" | cut -d',' -f1 | tr -d ' ')
      gpu_mem_used=$(echo "$gpu_line" | cut -d',' -f2 | tr -d ' ')
      gpu_mem_total=$(echo "$gpu_line" | cut -d',' -f3 | tr -d ' ')
      [[ -z "$gpu_util" || "$gpu_util" == "[N/A]" ]] && gpu_util="null"
      [[ -z "$gpu_mem_used" || "$gpu_mem_used" == "[N/A]" ]] && gpu_mem_used="null"
      [[ -z "$gpu_mem_total" || "$gpu_mem_total" == "[N/A]" ]] && gpu_mem_total="null"
    fi
  fi

  printf '{"ts":"%s","cpu_millicores":%s,"cpu_limit_millicores":%s,"memory_bytes":%s,"memory_limit_bytes":%s,"gpu_util_pct":%s,"gpu_mem_used_mib":%s,"gpu_mem_total_mib":%s}\n' \
    "$ts" \
    "${cpu_m:-0}" \
    "${CPU_LIMIT_MILLICORES:-2000}" \
    "${mem_b:-0}" \
    "${MEMORY_LIMIT_BYTES:-4294967296}" \
    "${gpu_util:-null}" \
    "${gpu_mem_used:-null}" \
    "${gpu_mem_total:-null}" >> "$log_file"
}

purge_old_logs

while true; do
  collect_once || true
  sleep "$INTERVAL_SEC"
done
