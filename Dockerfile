# docker run --name=codeserver --rm -it --init --gpus device=0 --ipc=host --user="$(id -u):$(id -g)" -v ./results:/results -v ./Custom_Benchmarking:/code -v ./tiny-imagenet-200:/data -p 8443:8443 -e PASSWORD=daovietanh99 daovietanh99/deepops
# docker run --name=codeserver --rm -it --init --gpus device=1 --ipc=host --user="$(id -u):$(id -g)" -v ./results:/results -v ./Custom_Benchmarking:/code -v ./imagenet:/data -p 8443:8443 -e PASSWORD=daovietanh99 -e WANDB_API_KEY=49d00f97c2faf751e194885af42b0d9ac4196b0f daovietanh99/deepops 
ARG FROM_IMAGE_NAME=nvcr.io/nvidia/pytorch:22.10-py3
FROM ${FROM_IMAGE_NAME}

USER root

ENV DEBIAN_FRONTEND noninteractive
# Set the locale
RUN apt-get update --yes && \
    # - apt-get upgrade is run to patch known vulnerabilities in apt-get packages as
    #   the ubuntu base image is rebuilt too seldom sometimes (less than once a month)
    apt-get upgrade --yes && \
    apt-get install --yes --no-install-recommends \
    # - bzip2 is necessary to extract the micromamba executable.
    bzip2 \
    ca-certificates \
    locales \
    sudo \
    build-essential \
    apt-utils \
    apt-transport-https \
    software-properties-common \
    pkg-config \
    curl \
    unzip \
    gpg-agent \
    screen \
    vim \
    sudo \
    dumb-init \
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
    # python3-opencv \
    # - tini is installed as a helpful container entrypoint that reaps zombie
    #   processes and such of the actual executable we want to start, see
    #   https://github.com/krallin/tini#why-tini for details.
    tini \
    wget && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen

RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN add-apt-repository universe
RUN apt-get update

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="${HOME}/.cargo/bin:${PATH}"
RUN pip3 install --upgrade pip
RUN pip3 install transformers
RUN pip3 install pandas
RUN pip3 install matplotlib
RUN pip3 install tensorboard
RUN pip3 install wheel
RUN pip3 install flask
RUN pip3 install fastapi
RUN pip3 install scikit-build
RUN pip3 install pytorch-lightning
RUN pip3 install torchsummary
RUN pip3 install ujson>=5.5.0
RUN pip3 install pybind11>=2.10.0
RUN pip3 install wandb
RUN pip3 install git+https://github.com/NVIDIA/dllogger.git#egg=dllogger
RUN pip3 install Cython>=0.29.32

RUN apt install -y libgl1-mesa-glx

RUN ln -s /usr/bin/python3 /usr/bin/python & \
    ln -s /usr/bin/pip3 /usr/bin/pip

# Create a non-root user
RUN adduser --disabled-password --gecos '' --shell /bin/bash coder
RUN echo "coder ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-coder

# Install fixuid
ENV ARCH=amd64
RUN curl -fsSL "https://github.com/boxboat/fixuid/releases/download/v0.4.1/fixuid-0.4.1-linux-$ARCH.tar.gz" | tar -C /usr/local/bin -xzf - && \
  chown root:root /usr/local/bin/fixuid && \
  chmod 4755 /usr/local/bin/fixuid && \
  mkdir -p /etc/fixuid && \
  printf "user: coder\ngroup: coder\n" > /etc/fixuid/config.yml

WORKDIR /tmp
RUN curl -fsSL https://code-server.dev/install.sh | sh

COPY ./entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod 4755 /usr/bin/entrypoint.sh

USER coder
ENV USER=coder
ENV HOME=/home/coder
WORKDIR /home/coder

EXPOSE 8443
ENTRYPOINT ["/usr/bin/entrypoint.sh", "--bind-addr", "0.0.0.0:8443", "--disable-telemetry", "."]
