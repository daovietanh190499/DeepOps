#!/usr/bin/env bash
# Build DeepOps (DoHub) Docker image and deploy the main Helm chart.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Defaults
IMAGE_REPO="${IMAGE_REPO:-daovietanh99/dohub}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
SSH_BRIDGE_REPO="${SSH_BRIDGE_REPO:-localhost:32000/ssh-bridge}"
SSH_BRIDGE_TAG="${SSH_BRIDGE_TAG:-${IMAGE_TAG}}"
SSH_BRIDGE_CONTEXT="${SSH_BRIDGE_CONTEXT:-./charts/codehub/ssh-bridge}"
KUBE_VERSION="${KUBE_VERSION:-1.30.0}"
HELM_VERSION="${HELM_VERSION:-3.14.4}"
TARGETOS="${TARGETOS:-linux}"
TARGETARCH="${TARGETARCH:-amd64}"
RELEASE_NAME="${RELEASE_NAME:-dohub}"
NAMESPACE="${NAMESPACE:-dohub}"
CHART_PATH="${CHART_PATH:-./dohub}"
VALUES_FILE="${VALUES_FILE:-}"
PUSH_IMAGE="${PUSH_IMAGE:-false}"
RESTART_DEPLOY="${RESTART_DEPLOY:-true}"
ACTION="all"

usage() {
  cat <<'EOF'
Usage: ./build-and-deploy.sh [OPTIONS] [COMMAND]

Commands:
  build     Build Docker images (dohub + ssh-bridge)
  deploy    Helm upgrade/install chart
  all       Build then deploy (default)

Options:
  -r, --repo REPO          DoHub image repository       (default: daovietanh99/dohub)
  -t, --tag TAG            DoHub image tag              (default: latest)
      --ssh-bridge-repo REPO ssh-bridge image repository (default: localhost:32000/ssh-bridge)
      --ssh-bridge-tag TAG   ssh-bridge image tag         (default: same as --tag)
  -n, --namespace NS       Kubernetes namespace        (default: dohub)
      --release NAME       Helm release name           (default: dohub)
      --chart PATH         Helm chart directory        (default: ./dohub)
  -f, --values FILE        Extra Helm values file (-f)
  -p, --push               Push image after build
      --no-push            Do not push (default)
      --no-restart         Skip kubectl rollout restart after deploy
      --kube-version VER   kubectl version in image    (default: 1.30.0)
      --helm-version VER   helm version in image       (default: 3.14.4)
      --platform OS/ARCH   docker build platform       (default: linux/amd64)
  -h, --help               Show this help

Environment (override flags):
  IMAGE_REPO, IMAGE_TAG, SSH_BRIDGE_REPO, SSH_BRIDGE_TAG, SSH_BRIDGE_CONTEXT,
  RELEASE_NAME, NAMESPACE, CHART_PATH, VALUES_FILE, PUSH_IMAGE,
  KUBE_VERSION, HELM_VERSION

Examples:
  ./build-and-deploy.sh build
  ./build-and-deploy.sh -r my.registry/dohub -t 1.2.0 -p build
  ./build-and-deploy.sh -n dohub-prod --release dohub deploy
  ./build-and-deploy.sh -r my.registry/dohub -t 1.2.0 -p -f dohub/values-prod.yaml all

Before deploy:
  1. cp dohub/secrets/.env.example dohub/secrets/.env
  2. Edit dohub/configmap/config.yaml and dohub/values.yaml
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      build|deploy|all)
        ACTION="$1"
        shift
        ;;
      -r|--repo)
        IMAGE_REPO="$2"
        shift 2
        ;;
      -t|--tag)
        IMAGE_TAG="$2"
        SSH_BRIDGE_TAG="${SSH_BRIDGE_TAG:-$2}"
        shift 2
        ;;
      --ssh-bridge-repo)
        SSH_BRIDGE_REPO="$2"
        shift 2
        ;;
      --ssh-bridge-tag)
        SSH_BRIDGE_TAG="$2"
        shift 2
        ;;
      -n|--namespace)
        NAMESPACE="$2"
        shift 2
        ;;
      --release)
        RELEASE_NAME="$2"
        shift 2
        ;;
      --chart)
        CHART_PATH="$2"
        shift 2
        ;;
      -f|--values)
        VALUES_FILE="$2"
        shift 2
        ;;
      -p|--push)
        PUSH_IMAGE=true
        shift
        ;;
      --no-push)
        PUSH_IMAGE=false
        shift
        ;;
      --no-restart)
        RESTART_DEPLOY=false
        shift
        ;;
      --kube-version)
        KUBE_VERSION="$2"
        shift 2
        ;;
      --helm-version)
        HELM_VERSION="$2"
        shift 2
        ;;
      --platform)
        TARGETOS="${2%%/*}"
        TARGETARCH="${2##*/}"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      --)
        shift
        break
        ;;
      -*)
        echo "Unknown option: $1" >&2
        usage >&2
        exit 1
        ;;
      *)
        echo "Unknown argument: $1" >&2
        usage >&2
        exit 1
        ;;
    esac
  done
}

build_dohub_image() {
  echo "==> Building dohub ${IMAGE_REPO}:${IMAGE_TAG} (${TARGETOS}/${TARGETARCH})"
  docker build \
    --build-arg KUBE_VERSION="${KUBE_VERSION}" \
    --build-arg HELM_VERSION="${HELM_VERSION}" \
    --build-arg TARGETOS="${TARGETOS}" \
    --build-arg TARGETARCH="${TARGETARCH}" \
    -t "${IMAGE_REPO}:${IMAGE_TAG}" \
    -f Dockerfile \
    .
  if [[ "${PUSH_IMAGE}" == "true" ]]; then
    echo "==> Pushing ${IMAGE_REPO}:${IMAGE_TAG}"
    docker push "${IMAGE_REPO}:${IMAGE_TAG}"
  fi
}

build_ssh_bridge_image() {
  if [[ ! -f "${SSH_BRIDGE_CONTEXT}/Dockerfile" ]]; then
    echo "ssh-bridge Dockerfile not found: ${SSH_BRIDGE_CONTEXT}/Dockerfile" >&2
    exit 1
  fi
  echo "==> Building ssh-bridge ${SSH_BRIDGE_REPO}:${SSH_BRIDGE_TAG} (${TARGETOS}/${TARGETARCH})"
  docker build \
    --build-arg TARGETARCH="${TARGETARCH}" \
    -t "${SSH_BRIDGE_REPO}:${SSH_BRIDGE_TAG}" \
    -f "${SSH_BRIDGE_CONTEXT}/Dockerfile" \
    "${SSH_BRIDGE_CONTEXT}"
  if [[ "${PUSH_IMAGE}" == "true" ]]; then
    echo "==> Pushing ${SSH_BRIDGE_REPO}:${SSH_BRIDGE_TAG}"
    docker push "${SSH_BRIDGE_REPO}:${SSH_BRIDGE_TAG}"
  fi
}

build_images() {
  build_dohub_image
  build_ssh_bridge_image
}

deploy_chart() {
  if [[ ! -f dohub/secrets/.env && ! -f "${CHART_PATH}/secrets/.env" ]]; then
    echo "Missing secrets/.env — run: cp dohub/secrets/.env.example dohub/secrets/.env" >&2
    exit 1
  fi
  if [[ ! -d "${CHART_PATH}" ]]; then
    echo "Chart not found: ${CHART_PATH}" >&2
    exit 1
  fi

  local -a helm_args=(
    upgrade --install "${RELEASE_NAME}" "${CHART_PATH}"
    --create-namespace
    --namespace "${NAMESPACE}"
    --reset-values
    --set "image.repository=${IMAGE_REPO}"
    --set "image.tag=${IMAGE_TAG}"
  )
  if [[ -n "${VALUES_FILE}" ]]; then
    if [[ ! -f "${VALUES_FILE}" ]]; then
      echo "Values file not found: ${VALUES_FILE}" >&2
      exit 1
    fi
    helm_args+=(-f "${VALUES_FILE}")
  fi

  echo "==> Deploying ${RELEASE_NAME} → namespace ${NAMESPACE}"
  echo "    Image: ${IMAGE_REPO}:${IMAGE_TAG}"
  echo "    ssh-bridge (workspace sidecar): ${SSH_BRIDGE_REPO}:${SSH_BRIDGE_TAG}"
  echo "    Chart: ${CHART_PATH}"
  microk8s helm "${helm_args[@]}"

  if [[ "${RESTART_DEPLOY}" == "true" ]]; then
    microk8s kubectl rollout restart "deployment/${RELEASE_NAME}" -n "${NAMESPACE}" 2>/dev/null || \
      microk8s kubectl rollout restart "deploy/${RELEASE_NAME}" -n "${NAMESPACE}" 2>/dev/null || true
  fi
  echo "==> Done. Check ingress host in ${CHART_PATH}/values.yaml"
}

main() {
  parse_args "$@"

  case "${ACTION}" in
    build) build_images ;;
    deploy) deploy_chart ;;
    all) build_images; deploy_chart ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
