FROM ubuntu:22.04

USER root
WORKDIR /app

RUN apt-get update --yes && \
    apt-get upgrade --yes && \
    apt-get install --yes --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    jq \
    tzdata \
    python3 \
    python3-pip \
    python3-venv && \
    rm -rf /var/lib/apt/lists/*

ARG KUBE_VERSION=1.30.0
ARG HELM_VERSION=3.14.4
ARG TARGETOS=linux
ARG TARGETARCH=amd64

RUN wget -q "https://dl.k8s.io/release/v${KUBE_VERSION}/bin/${TARGETOS}/${TARGETARCH}/kubectl" -O /usr/local/bin/kubectl && \
    wget -q "https://get.helm.sh/helm-v${HELM_VERSION}-${TARGETOS}-${TARGETARCH}.tar.gz" -O /tmp/helm.tgz && \
    tar -xzf /tmp/helm.tgz -C /tmp && \
    mv "/tmp/${TARGETOS}-${TARGETARCH}/helm" /usr/local/bin/helm && \
    chmod +x /usr/local/bin/kubectl /usr/local/bin/helm && \
    kubectl version --client && \
    helm version

COPY DeepOpsBackend/requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

COPY DeepOpsBackend /app
COPY charts/codehub /charts/codehub

# Add kubectl-directpv to path this will need to update by the version of directpv
COPY ./kubectl-directpv /usr/local/bin/kubectl-directpv
RUN chmod +x /usr/local/bin/kubectl-directpv

ENV CODEHUB_CHART_PATH=/charts/codehub
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=DeepOpsBackend.settings
ENV TZ=UTC

RUN python3 manage.py collectstatic --noinput

EXPOSE 5000

CMD ["/bin/bash", "-c", "python3 manage.py migrate --noinput && gunicorn DeepOpsBackend.wsgi:application --bind 0.0.0.0:5000 --workers 2 --timeout 120"]
