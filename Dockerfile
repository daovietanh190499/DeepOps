FROM ubuntu:20.04

USER root

WORKDIR /home/dohub

RUN apt-get update --yes && \
    # - apt-get upgrade is run to patch known vulnerabilities in apt-get packages as
    #   the ubuntu base image is rebuilt too seldom sometimes (less than once a month)
    apt-get upgrade --yes && \
    apt-get install --yes --no-install-recommends \
    dumb-init \
    apt-transport-https \
    ca-certificates \ 
    curl \
    wget \
    jq \
    gettext \
    python3-pip

ARG KUBE_VERSION
ARG HELM_VERSION
ARG TARGETOS
ARG TARGETARCH

RUN wget -q https://storage.googleapis.com/kubernetes-release/release/v${KUBE_VERSION}/bin/${TARGETOS}/${TARGETARCH}/kubectl -O /usr/local/bin/kubectl \
    && wget -q https://get.helm.sh/helm-v${HELM_VERSION}-${TARGETOS}-${TARGETARCH}.tar.gz -O - | tar -xzO ${TARGETOS}-${TARGETARCH}/helm > /usr/local/bin/helm \
    && chmod +x /usr/local/bin/helm /usr/local/bin/kubectl \
    && mkdir /config \
    && chmod g+rwx /config /root \
    && helm repo add "stable" "https://charts.helm.sh/stable" --force-update \
    && kubectl version --client \
    && helm version

COPY ./requirement.txt ./requirement.txt

RUN pip3 install -r requirement.txt

COPY . .

USER root
ENV USER=root
ENV HOME=/home/dohub

WORKDIR /home/dohub