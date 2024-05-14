# docker run --name=codeserver --rm -it --init --gpus device=0 --ipc=host --user="$(id -u):$(id -g)" -v ./results:/results -v ./Custom_Benchmarking:/code -v ./tiny-imagenet-200:/data -p 8443:8443 -e PASSWORD=daovietanh99 daovietanh99/deepops
# docker run --name=codeserver --rm -it --init --gpus device=1 --ipc=host --user="$(id -u):$(id -g)" -v ./results:/results -v ./Custom_Benchmarking:/code -v ./imagenet:/data -p 8443:8443 -e PASSWORD=daovietanh99 -e WANDB_API_KEY=49d00f97c2faf751e194885af42b0d9ac4196b0f daovietanh99/deepops 
ARG FROM_IMAGE_NAME=nvcr.io/nvidia/pytorch:22.10-py3
FROM ${FROM_IMAGE_NAME}

USER root

ENV DEBIAN_FRONTEND noninteractive

RUN ln -s /usr/bin/python3 /usr/bin/python & \
    ln -s /usr/bin/pip3 /usr/bin/pip

# Install fixuid
ENV ARCH=amd64
RUN curl -fsSL "https://github.com/boxboat/fixuid/releases/download/v0.4.1/fixuid-0.4.1-linux-$ARCH.tar.gz" | tar -C /usr/local/bin -xzf - && \
  chown root:root /usr/local/bin/fixuid && \
  chmod 4755 /usr/local/bin/fixuid && \
  mkdir -p /etc/fixuid && \
  printf "user: coder\ngroup: coder\n" > /etc/fixuid/config.yml

RUN apt-get update --yes && \ 
    apt-get install --yes --no-install-recommends zsh
RUN chsh -s $(which zsh)
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

RUN apt-get update --yes && \
    apt-get upgrade --yes && \
    apt-get install --yes --no-install-recommends \
    bzip2 \
    ca-certificates \
    locales \
    sudo \
    build-essential \
    apt-utils \
    apt-transport-https \
    software-properties-common \
    pkg-config \
    unzip \
    gpg-agent \
    screen \
    vim \
    sudo \
    htop \
    git \
    bzip2 \
    libx11-6 \
    man \
    nano \
    procps \
    openssh-client \
    vim.tiny \
    lsb-release \
    postgresql \
    postgresql-contrib \
    net-tools \
    tmux \
    # python3-opencv \
    wget \
    libgl1-mesa-glx

WORKDIR /tmp
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Create a non-root user
RUN adduser --disabled-password --gecos '' --shell /bin/bash coder
RUN echo "coder ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-coder

COPY ./entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod 4755 /usr/bin/entrypoint.sh

USER coder
ENV USER=coder
ENV HOME=/home/coder
WORKDIR /home/coder
