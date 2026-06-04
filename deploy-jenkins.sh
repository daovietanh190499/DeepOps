#!/usr/bin/env bash
# Deploy full Jenkins from charts/jenkins
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

RELEASE_NAME="${RELEASE_NAME:-jenkins}"
NAMESPACE="${NAMESPACE:-jenkins}"
VALUES_FILE="${VALUES_FILE:-}"

usage() {
  cat <<'EOF'
Usage: ./deploy-jenkins.sh [install|uninstall|lint]

  install   - helm upgrade --install (default)
  uninstall - helm uninstall
  lint      - helm lint chart

Environment:
  RELEASE_NAME, NAMESPACE
  VALUES_FILE=/path/to/values.yaml  - optional extra values
  JENKINS_ADMIN_PASSWORD            - passed via --set if set

Example:
  JENKINS_ADMIN_PASSWORD='secret' ./deploy-jenkins.sh install
EOF
}

lint_chart() {
  helm lint ./charts/jenkins
}

install_chart() {
  local -a extra_args=()
  if [[ -n "${VALUES_FILE}" && -f "${VALUES_FILE}" ]]; then
    extra_args+=(-f "${VALUES_FILE}")
  fi
  if [[ -n "${JENKINS_ADMIN_PASSWORD:-}" ]]; then
    extra_args+=(--set "controller.adminPassword=${JENKINS_ADMIN_PASSWORD}")
  fi

  helm upgrade --install "${RELEASE_NAME}" ./charts/jenkins \
    --create-namespace \
    --namespace "${NAMESPACE}" \
    "${extra_args[@]}"

  echo ""
  echo "Jenkins deployed. Get admin password:"
  echo "  kubectl get secret ${RELEASE_NAME}-admin -n ${NAMESPACE} -o jsonpath='{.data.jenkins-admin-password}' | base64 -d; echo"
}

uninstall_chart() {
  helm uninstall "${RELEASE_NAME}" -n "${NAMESPACE}"
}

ACTION="${1:-install}"
case "${ACTION}" in
  -h|--help) usage ;;
  lint) lint_chart ;;
  install) install_chart ;;
  uninstall) uninstall_chart ;;
  *) usage; exit 1 ;;
esac
