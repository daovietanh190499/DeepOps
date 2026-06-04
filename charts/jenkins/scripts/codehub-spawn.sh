#!/usr/bin/env bash
# Spawn a codehub release — DirectPV PVC (no NFS)
set -euo pipefail

USERNAME="${USERNAME:?USERNAME is required}"
PASSWORD="${PASSWORD:?PASSWORD is required}"

CPU="${CPU:-2}"
RAM="${RAM:-4G}"
GPU="${GPU:-none}"
DOCKER_IMAGE="${DOCKER_IMAGE:-codercom/code-server}"
IMAGE_TAG="${IMAGE_TAG:-4.89.0-ubuntu}"
VOLUME_SIZE="${VOLUME_SIZE:-20Gi}"
STORAGE_CLASS="${STORAGE_CLASS:-directpv-min-io}"
NAMESPACE="${NAMESPACE:-dohub}"
DOMAIN_NAME="${DOMAIN_NAME:-dohub.com}"
DEFAULT_PORT="${DEFAULT_PORT:-8080}"
CODEHUB_CHART_PATH="${CODEHUB_CHART_PATH:-./charts/codehub}"
SKIP_HELM="${SKIP_HELM:-false}"

if [[ ! -d "${CODEHUB_CHART_PATH}" ]]; then
  echo "CODEHUB_CHART_PATH not found: ${CODEHUB_CHART_PATH}" >&2
  exit 1
fi

MAX_CPU="$(awk -v c="${CPU}" 'BEGIN { printf "%g", c * 1.5 }')"
if [[ "${RAM}" == *G ]]; then
  RAM_VALUE="${RAM%G}"
  MAX_RAM_VALUE="$(awk -v r="${RAM_VALUE}" 'BEGIN { printf "%d", r * 1.5 }')"
  MAX_RAM="${MAX_RAM_VALUE}G"
else
  MAX_RAM="${RAM}"
fi

GPU_FLAGS=()
if [[ -n "${GPU}" && "${GPU}" != "none" && "${GPU}" != "null" && "${GPU}" != "" ]]; then
  if [[ "${GPU}" == *:* ]]; then
    GPU_RESOURCE="${GPU%%:*}"
    GPU_QUANTITY="${GPU##*:}"
  else
    GPU_RESOURCE="${GPU}"
    GPU_QUANTITY="1"
  fi
  GPU_KEY="nvidia.com/${GPU_RESOURCE}"
  GPU_FLAGS=(
    --set "resources.limits.${GPU_KEY}=${GPU_QUANTITY}"
    --set "resources.requests.${GPU_KEY}=${GPU_QUANTITY}"
  )
fi

RELEASE_NAME="${NAMESPACE}-${USERNAME}"
CLAIM_NAME="claim-${NAMESPACE}-${USERNAME}"
INGRESS_HOST="${USERNAME}.${DOMAIN_NAME}"

HELM_CMD=(
  helm upgrade --install --create-namespace
  -n "${NAMESPACE}"
  --set "image.repository=${DOCKER_IMAGE}"
  --set image.pullPolicy=IfNotPresent
  --set "image.tag=${IMAGE_TAG}"
  --set "podLabels.${NAMESPACE}-username=${USERNAME}"
  --set "secret.name=${USERNAME}-secret"
  --set-string "env.secret.PASSWORD=${PASSWORD}"
  --set auth.resetConfigOnDeploy=true
  --set serviceAccount.create=false
  --set serviceAccount.automount=false
  --set serviceAccount.name=default
  --set podSecurityContext.fsGroup=100
  --set securityContext.capabilities.add[0]=SYS_ADMIN
  --set securityContext.allowPrivilegeEscalation=true
  --set securityContext.runAsUser=0
  --set service.type=ClusterIP
  --set "service.port=${DEFAULT_PORT}"
  --set ingress.enabled=true
  --set-string ingress.annotations.nginx\.ingress\.kubernetes\.io/proxy-body-size=0
  --set-string ingress.annotations.nginx\.ingress\.kubernetes\.io/proxy-read-timeout=600
  --set-string ingress.annotations.nginx\.ingress\.kubernetes\.io/proxy-send-timeout=600
  --set-string ingress.annotations.nginx\.ingress\.kubernetes\.io/proxy-buffering=off
  --set-string ingress.annotations.nginx\.ingress\.kubernetes\.io/proxy-http-version=1.1
  --set trustProxy=true
  --set ingress.className=nginx
  --set "ingress.hosts[0].host=${INGRESS_HOST}"
  --set ingress.hosts[0].paths[0].path=/
  --set ingress.hosts[0].paths[0].pathType=Prefix
  --set "ingress.tls[0].secretName=tls-${NAMESPACE}-secret"
  --set "ingress.tls[0].hosts[0]=${INGRESS_HOST}"
  --set persistence.enabled=true
  --set "persistence.claimName=${CLAIM_NAME}"
  --set "mainVolume.claimName=${CLAIM_NAME}"
  --set "persistence.storageClassName=${STORAGE_CLASS}"
  --set persistence.volumeMode=Filesystem
  --set "persistence.size=${VOLUME_SIZE}"
  --set volumes[0].name=shm-volume
  --set volumes[0].emptyDir.medium=Memory
  --set "resources.limits.cpu=${MAX_CPU}"
  --set "resources.limits.memory=${MAX_RAM}"
  --set "resources.requests.cpu=${CPU}"
  --set "resources.requests.memory=${RAM}"
  "${GPU_FLAGS[@]}"
  "${RELEASE_NAME}"
  "${CODEHUB_CHART_PATH}"
)

echo "==> DirectPV PVC: ${CLAIM_NAME} (${VOLUME_SIZE}, ${STORAGE_CLASS})"
printf ' %q' "${HELM_CMD[@]}"
echo

if [[ "${SKIP_HELM}" == "true" ]]; then
  exit 0
fi

"${HELM_CMD[@]}"
echo "==> Spawned ${RELEASE_NAME}"
kubectl get pvc,pods -n "${NAMESPACE}" -l "${NAMESPACE}-username=${USERNAME}" 2>/dev/null || true
