#!/usr/bin/env bash
# Test / debug codehub spawn (same logic as DeepOpsBackend + UI Start Server)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Load env (hub pod uses dohub/secrets/.env)
ENV_FILE="${ENV_FILE:-$ROOT/dohub/secrets/.env}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
  echo "==> Loaded env from $ENV_FILE"
fi

USERNAME="${USERNAME:-}"
PASSWORD="${PASSWORD:-}"
NAMESPACE="${NAMESPACE:-dohub}"
DOMAIN_NAME="${DOMAIN_NAME:-dohub.com}"
CODEHUB_CHART_PATH="${CODEHUB_CHART_PATH:-$ROOT/charts/codehub}"
HUB_RELEASE="${HUB_RELEASE:-dohub}"
SKIP_HELM="${SKIP_HELM:-false}"
FROM_HUB_POD="${FROM_HUB_POD:-false}"

usage() {
  cat <<'EOF'
Usage: ./test-codehub.sh <command> [options]

Commands:
  preflight     Check helm, kubectl, chart, storage class, hub deployment
  spawn         Run helm upgrade (same as backend create_codehub)
  status        Show helm release, pods, pvc, events for USERNAME
  delete        helm uninstall codehub release for USERNAME
  hub-exec      Run spawn inside hub pod (tests in-cluster RBAC + chart path)
  api-start     Call POST /start_server/USERNAME (needs COOKIE)

Environment / flags:
  USERNAME          GitHub username (required for spawn/status/delete/api)
  PASSWORD          Code-server password (required for spawn)
  CPU RAM GPU       Plan resources (default: 2, 4G, none)
  VOLUME_SIZE       DirectPV size (default: 20Gi)
  STORAGE_CLASS     default: directpv-min-io
  NAMESPACE         default: dohub
  DOMAIN_NAME       default from .env
  CODEHUB_CHART_PATH  default: ./charts/codehub
  ENV_FILE          default: ./dohub/secrets/.env
  HUB_URL           for api-start, e.g. https://iaihub.uet.edu.vn
  COOKIE            user_access_key value for api-start
  SKIP_HELM=1       Print helm command only (spawn / hub-exec)

Examples:
  ./test-codehub.sh preflight
  USERNAME=alice PASSWORD=secret ./test-codehub.sh spawn
  USERNAME=alice ./test-codehub.sh status
  USERNAME=alice ./test-codehub.sh delete
  FROM_HUB_POD=1 USERNAME=alice PASSWORD=secret ./test-codehub.sh hub-exec
  HUB_URL=https://your-hub COOKIE=xxx USERNAME=alice ./test-codehub.sh api-start
EOF
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1" >&2; exit 1; }
}

preflight() {
  echo "========== Preflight =========="
  need_cmd kubectl
  need_cmd helm
  echo "kubectl: $(kubectl version --client 2>/dev/null | head -1)"
  echo "helm:    $(helm version --short 2>/dev/null || helm version | head -1)"
  echo ""
  echo "Context: $(kubectl config current-context 2>/dev/null || echo '?')"
  echo "NAMESPACE=$NAMESPACE  DOMAIN_NAME=$DOMAIN_NAME"
  echo "CODEHUB_CHART_PATH=$CODEHUB_CHART_PATH"
  echo ""

  if [[ ! -d "$CODEHUB_CHART_PATH" ]]; then
    echo "FAIL: chart not found at $CODEHUB_CHART_PATH"
    exit 1
  fi
  echo "OK: chart exists ($(helm show chart "$CODEHUB_CHART_PATH" 2>/dev/null | head -3))"

  if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
    echo "WARN: namespace $NAMESPACE does not exist (helm --create-namespace will create it)"
  else
    echo "OK: namespace $NAMESPACE"
  fi

  echo ""
  echo "--- StorageClass (DirectPV) ---"
  SC="${STORAGE_CLASS:-directpv-min-io}"
  if kubectl get storageclass "$SC" &>/dev/null; then
    kubectl get storageclass "$SC" -o wide
  else
    echo "FAIL: StorageClass '$SC' not found. Install DirectPV or set STORAGE_CLASS."
  fi

  echo ""
  echo "--- Hub deployment ($HUB_RELEASE in $NAMESPACE) ---"
  if kubectl get deploy -n "$NAMESPACE" -l "app.kubernetes.io/instance=$HUB_RELEASE" -o name 2>/dev/null | head -1; then
    kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$HUB_RELEASE" -o wide
    HUB_POD=$(kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$HUB_RELEASE" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
    if [[ -n "$HUB_POD" ]]; then
      echo ""
      echo "Hub pod tools:"
      kubectl exec -n "$NAMESPACE" "$HUB_POD" -- sh -c 'which helm kubectl; ls -la /charts/codehub/Chart.yaml 2>/dev/null || echo "MISSING /charts/codehub"'
      echo ""
      echo "Hub env (spawn-related):"
      kubectl exec -n "$NAMESPACE" "$HUB_POD" -- sh -c 'echo SPAWNER=$SPAWNER NAMESPACE=$NAMESPACE CODEHUB_CHART_PATH=$CODEHUB_CHART_PATH DOMAIN_NAME=$DOMAIN_NAME'
    fi
  else
    echo "WARN: hub deployment not found — is helm release '$HUB_RELEASE' deployed?"
  fi

  echo ""
  echo "--- Common UI 'Start' blockers ---"
  echo "  1. User is_accept=false in DB (admin must Accept)"
  echo "  2. SPAWNER must be 'k8s' in hub .env"
  echo "  3. Hub ServiceAccount needs RBAC to run helm/kubectl in $NAMESPACE"
  echo "  4. API returns success even if helm fails — check spawn logs in JSON response"
  echo "  5. state must be offline (non-admin) before start"
}

run_spawn_local() {
  [[ -n "$USERNAME" ]] || { echo "Set USERNAME=" >&2; exit 1; }
  [[ -n "$PASSWORD" ]] || { echo "Set PASSWORD=" >&2; exit 1; }
  export USERNAME PASSWORD
  export CODEHUB_CHART_PATH
  export NAMESPACE DOMAIN_NAME
  export CPU="${CPU:-2}" RAM="${RAM:-4G}" GPU="${GPU:-none}"
  export VOLUME_SIZE="${VOLUME_SIZE:-20Gi}"
  export STORAGE_CLASS="${STORAGE_CLASS:-directpv-min-io}"
  export SKIP_HELM
  echo "========== Spawn (local shell) =========="
  bash "$ROOT/charts/jenkins/scripts/codehub-spawn.sh"
  echo ""
  status
}

run_spawn_in_hub() {
  [[ -n "$USERNAME" ]] || { echo "Set USERNAME=" >&2; exit 1; }
  [[ -n "$PASSWORD" ]] || { echo "Set PASSWORD=" >&2; exit 1; }
  HUB_POD=$(kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$HUB_RELEASE" -o jsonpath='{.items[0].metadata.name}')
  [[ -n "$HUB_POD" ]] || { echo "Hub pod not found" >&2; exit 1; }

  echo "========== Spawn inside hub pod: $HUB_POD =========="
  SCRIPT=$(cat <<'PODSCRIPT'
set -e
export USERNAME='__USER__'
export PASSWORD='__PASS__'
export CPU='__CPU__'
export RAM='__RAM__'
export GPU='__GPU__'
export VOLUME_SIZE='__VOL__'
export NAMESPACE='__NS__'
export DOMAIN_NAME='__DOM__'
export CODEHUB_CHART_PATH=/charts/codehub
export SKIP_HELM='__SKIP__'
CHART=/charts/codehub
if [[ ! -f "$CHART/Chart.yaml" ]]; then echo "FAIL: $CHART missing in pod"; exit 1; fi
# Minimal helm (same sets as backend)
CLAIM="claim-${NAMESPACE}-${USERNAME}"
REL="${NAMESPACE}-${USERNAME}"
GPU_SET=""
if [[ "$GPU" != "none" && -n "$GPU" ]]; then
  G="${GPU%%:*}"; Q="${GPU##*:}"; [[ "$GPU" != *:* ]] && Q=1
  GPU_SET="--set resources.limits.nvidia.com/${G}=${Q} --set resources.requests.nvidia.com/${G}=${Q}"
fi
MAX_CPU=$(awk -v c="$CPU" 'BEGIN{printf "%g", c*1.5}')
RAMN=${RAM%G}; MAX_RAM=$(awk -v r="$RAMN" 'BEGIN{printf "%d", r*1.5}')G
CMD="helm upgrade --install --create-namespace -n $NAMESPACE \
  --set image.repository=codercom/code-server --set image.tag=4.89.0-ubuntu \
  --set podLabels.${NAMESPACE}-username=$USERNAME \
  --set secret.name=${USERNAME}-secret --set env.secret.PASSWORD=$PASSWORD \
  --set persistence.enabled=true --set persistence.claimName=$CLAIM \
  --set persistence.storageClassName=directpv-min-io --set persistence.size=$VOLUME_SIZE \
  --set ingress.hosts[0].host=${USERNAME}.${DOMAIN_NAME} \
  $GPU_SET $REL $CHART"
echo "$CMD"
if [[ "$SKIP_HELM" == "true" ]]; then exit 0; fi
eval "$CMD"
echo "==> helm exit: $?"
kubectl get pods,pvc -n "$NAMESPACE" -l "${NAMESPACE}-username=${USERNAME}" 2>/dev/null || true
PODSCRIPT
)
  SCRIPT="${SCRIPT//__USER__/$USERNAME}"
  SCRIPT="${SCRIPT//__PASS__/$PASSWORD}"
  SCRIPT="${SCRIPT//__CPU__/${CPU:-2}}"
  SCRIPT="${SCRIPT//__RAM__/${RAM:-4G}}"
  SCRIPT="${SCRIPT//__GPU__/${GPU:-none}}"
  SCRIPT="${SCRIPT//__VOL__/${VOLUME_SIZE:-20Gi}}"
  SCRIPT="${SCRIPT//__NS__/$NAMESPACE}"
  SCRIPT="${SCRIPT//__DOM__/$DOMAIN_NAME}"
  SCRIPT="${SCRIPT//__SKIP__/$SKIP_HELM}"

  kubectl exec -n "$NAMESPACE" "$HUB_POD" -- bash -c "$SCRIPT"
}

status() {
  [[ -n "$USERNAME" ]] || { echo "Set USERNAME=" >&2; exit 1; }
  REL="${NAMESPACE}-${USERNAME}"
  echo "========== Status: $USERNAME =========="
  echo "--- Helm release $REL ---"
  helm list -n "$NAMESPACE" -f "^${REL}$" 2>/dev/null || helm list -n "$NAMESPACE" | grep "$REL" || echo "(not installed)"
  echo ""
  echo "--- Pods (label ${NAMESPACE}-username=$USERNAME) ---"
  kubectl get pods -n "$NAMESPACE" -l "${NAMESPACE}-username=${USERNAME}" -o wide 2>/dev/null || echo "(none)"
  echo ""
  echo "--- PVC ---"
  kubectl get pvc -n "$NAMESPACE" "claim-${NAMESPACE}-${USERNAME}" 2>/dev/null || kubectl get pvc -n "$NAMESPACE" | grep "$USERNAME" || echo "(none)"
  echo ""
  echo "--- Recent events in $NAMESPACE ---"
  kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' 2>/dev/null | tail -15
  echo ""
  P=$(kubectl get pods -n "$NAMESPACE" -l "${NAMESPACE}-username=${USERNAME}" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
  if [[ -n "$P" ]]; then
    echo "--- Pod describe (last 40 lines) ---"
    kubectl describe pod -n "$NAMESPACE" "$P" 2>/dev/null | tail -40
  fi
}

delete_release() {
  [[ -n "$USERNAME" ]] || { echo "Set USERNAME=" >&2; exit 1; }
  REL="${NAMESPACE}-${USERNAME}"
  echo "Uninstalling $REL ..."
  helm uninstall -n "$NAMESPACE" "$REL" 2>/dev/null || echo "Release not found"
  echo "Done. PVC may remain: kubectl delete pvc claim-${NAMESPACE}-${USERNAME} -n $NAMESPACE"
}

api_start() {
  [[ -n "$HUB_URL" ]] || { echo "Set HUB_URL=https://your-hub-domain" >&2; exit 1; }
  [[ -n "$COOKIE" ]] || { echo "Set COOKIE=<user_access_key from browser>" >&2; exit 1; }
  [[ -n "$USERNAME" ]] || { echo "Set USERNAME=" >&2; exit 1; }
  echo "========== API POST $HUB_URL/start_server/$USERNAME =========="
  RESP=$(curl -sS -w "\nHTTP_CODE:%{http_code}" -X POST \
    -H "Cookie: user_access_key=$COOKIE" \
    "$HUB_URL/start_server/$USERNAME")
  echo "$RESP"
  echo ""
  echo "If HTTP 200 but no pod: read 'logs' field — helm may have failed."
}

CMD="${1:-preflight}"
shift || true
case "$CMD" in
  -h|--help|help) usage ;;
  preflight) preflight ;;
  spawn)
    if [[ "$FROM_HUB_POD" == "true" || "$FROM_HUB_POD" == "1" ]]; then run_spawn_in_hub; else run_spawn_local; fi ;;
  hub-exec) FROM_HUB_POD=true; run_spawn_in_hub ;;
  status) status ;;
  delete) delete_release ;;
  api-start) api_start ;;
  *)
    echo "Unknown command: $CMD" >&2
    usage
    exit 1
    ;;
esac
