FROM debian:bookworm-slim

ARG KUBECTL_VERSION=v1.29.6
ARG TARGETARCH=amd64

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates curl coreutils && \
    rm -rf /var/lib/apt/lists/*

RUN case "${TARGETARCH}" in \
      amd64) KUBE_ARCH=amd64 ;; \
      arm64) KUBE_ARCH=arm64 ;; \
      *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac && \
    curl -fsSL \
      "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${KUBE_ARCH}/kubectl" \
      -o /usr/local/bin/kubectl && \
    chmod +x /usr/local/bin/kubectl && \
    kubectl version --client=true

WORKDIR /app
COPY collect.sh entrypoint.sh ./
RUN chmod +x /app/collect.sh /app/entrypoint.sh

ENV LOG_DIR=/tmp/monitor
ENV INTERVAL_SEC=2
ENV RETENTION_DAYS=30
ENV TARGET_CONTAINER=codehub
ENV GPU_ENABLED=false
ENV CPU_LIMIT_MILLICORES=2000
ENV MEMORY_LIMIT_BYTES=4294967296

CMD ["/app/entrypoint.sh"]
