FROM ubuntu:20.04

USER root

WORKDIR /home/dohub

COPY . .

RUN apt-get update --yes && \
    # - apt-get upgrade is run to patch known vulnerabilities in apt-get packages as
    #   the ubuntu base image is rebuilt too seldom sometimes (less than once a month)
    apt-get upgrade --yes && \
    apt-get install --yes --no-install-recommends \
    dumb-init \
    python3-pip

RUN pip3 install -r requirement.txt

USER root
ENV USER=root
ENV HOME=/home/dohub

WORKDIR /home/dohub

EXPOSE 5000
ENTRYPOINT ["dumb-init", "python3", "app.py"]