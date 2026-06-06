FROM python:3.11-slim-bookworm

ARG WSTUNNEL_VERSION=10.4.4
ARG TARGETARCH=amd64

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates curl tar && \
    rm -rf /var/lib/apt/lists/*

# Map docker TARGETARCH to wstunnel release arch names
RUN case "${TARGETARCH}" in \
      amd64) WST_ARCH=amd64 ;; \
      arm64) WST_ARCH=arm64 ;; \
      *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac && \
    curl -fsSL \
      "https://github.com/erebe/wstunnel/releases/download/v${WSTUNNEL_VERSION}/wstunnel_${WSTUNNEL_VERSION}_linux_${WST_ARCH}.tar.gz" \
      -o /tmp/wstunnel.tgz && \
    tar -xzf /tmp/wstunnel.tgz -C /usr/local/bin && \
    chmod +x /usr/local/bin/wstunnel && \
    rm /tmp/wstunnel.tgz && \
    wstunnel --version

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py entrypoint.sh ./
RUN chmod +x /app/entrypoint.sh

ENV SSH_BIND_HOST=127.0.0.1
ENV SSH_PORT=2222
ENV WS_PORT=8022
ENV WS_PATH_PREFIX=ssh-tunnel
ENV AUTHORIZED_KEYS=/ssh/authorized_keys
ENV HOST_KEY=/ssh-data/host_key
ENV SSH_USER=coder

EXPOSE 8022

CMD ["/app/entrypoint.sh"]
