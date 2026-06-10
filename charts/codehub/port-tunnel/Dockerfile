FROM debian:bookworm-slim

ARG WSTUNNEL_VERSION=10.4.4
ARG TARGETARCH=amd64

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates curl tar && \
    rm -rf /var/lib/apt/lists/*

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
COPY entrypoint.sh ./
RUN chmod +x /app/entrypoint.sh

ENV WS_PORT=8033
ENV WS_PATH_PREFIX=port-tunnel
ENV TARGET_HOST=127.0.0.1
ENV TUNNEL_PORTS=""

EXPOSE 8033

CMD ["/app/entrypoint.sh"]
