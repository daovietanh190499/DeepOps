FROM debian:bookworm-slim

ARG TARGETARCH=amd64

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates curl cron jq coreutils unzip procps && \
    rm -rf /var/lib/apt/lists/*

RUN case "${TARGETARCH}" in \
      amd64) RCLONE_ARCH=amd64 ;; \
      arm64) RCLONE_ARCH=arm64 ;; \
      *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac && \
    curl -fsSL \
      "https://downloads.rclone.org/rclone-current-linux-${RCLONE_ARCH}.zip" \
      -o /tmp/rclone.zip && \
    unzip -q /tmp/rclone.zip -d /tmp && \
    install -m 0755 "/tmp/rclone-"*"-linux-${RCLONE_ARCH}/rclone" /usr/local/bin/rclone && \
    rm -rf /tmp/rclone.zip /tmp/rclone-*-linux-${RCLONE_ARCH} && \
    apt-get purge -y unzip && apt-get autoremove -y && rm -rf /var/lib/apt/lists/* && \
    rclone version

WORKDIR /app
COPY entrypoint.sh run-backup.sh supervisor.sh ./
RUN chmod +x /app/entrypoint.sh /app/run-backup.sh /app/supervisor.sh

ENV LOG_DIR=/tmp/backup
ENV RCLONE_CONFIG=/config/rclone.conf
ENV BACKUP_REMOTE=""
ENV BACKUP_FOLDERS="[]"
ENV BACKUP_SCHEDULE=""

CMD ["/app/entrypoint.sh"]
