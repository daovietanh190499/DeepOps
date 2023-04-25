FROM python:3.9.16-bullseye

USER root

WORKDIR /home/dohub

COPY . .

RUN apt-get update --yes && \
    # - apt-get upgrade is run to patch known vulnerabilities in apt-get packages as
    #   the ubuntu base image is rebuilt too seldom sometimes (less than once a month)
    apt-get upgrade --yes && \
    apt-get install --yes --no-install-recommends \
    dumb-init

RUN pip install -r requirement.txt

EXPOSE 5000
ENTRYPOINT ["dumb-init", "/usr/bin/python3", "app.py"]