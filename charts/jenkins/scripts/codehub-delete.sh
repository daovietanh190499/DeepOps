#!/usr/bin/env bash
# Remove a codehub release — same as DeepOpsBackend remove_codehub(username)
set -euo pipefail

USERNAME="${USERNAME:?USERNAME is required}"
NAMESPACE="${NAMESPACE:-dohub}"
SKIP_HELM="${SKIP_HELM:-false}"

RELEASE_NAME="${NAMESPACE}-${USERNAME}"

echo "==> Removing Helm release: ${RELEASE_NAME} (namespace: ${NAMESPACE})"

if [[ "${SKIP_HELM}" == "true" ]]; then
  echo "Would run: helm uninstall -n ${NAMESPACE} ${RELEASE_NAME}"
  exit 0
fi

if helm status "${RELEASE_NAME}" -n "${NAMESPACE}" >/dev/null 2>&1; then
  helm uninstall -n "${NAMESPACE}" "${RELEASE_NAME}"
  echo "==> Uninstalled ${RELEASE_NAME}"
else
  echo "==> Release ${RELEASE_NAME} not found (already removed?)"
fi

# Optional: wait for pods to terminate
kubectl wait --for=delete pod -l "${NAMESPACE}-username=${USERNAME}" -n "${NAMESPACE}" --timeout=120s 2>/dev/null || true

echo "==> Done"
