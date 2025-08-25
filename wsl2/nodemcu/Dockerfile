# see https://hub.docker.com/_/ubuntu/ for versions, should be the same as on Travis for NodeMCU CI
# 16.04 == xenial
FROM ubuntu:22.04
LABEL maintainer="junand"

# Lint the final file with https://hadolint.github.io/hadolint/

# Deleting apt-get lists is done at the very end
# hadolint ignore=DL3009

RUN apt-get update
# https://serverfault.com/questions/949991/how-to-install-tzdata-on-a-ubuntu-docker-image
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
RUN apt-get update && apt-get install -y --no-install-recommends wget unzip git make python3-serial srecord bc xz-utils gcc ccache tzdata vim-tiny

# additionally required for ESP32 builds as per https://nodemcu.readthedocs.io/en/dev-esp32/build/#ubuntu
RUN apt-get install -y --no-install-recommends gperf python3-pip python3-dev flex bison build-essential libssl-dev libffi-dev libncurses5-dev libncursesw5-dev libreadline-dev

# neccessary for idf4
RUN apt-get install -y --no-install-recommends libusb-1.0 cmake

# neccessary for idf5
RUN apt-get install -y --no-install-recommends python3-venv

RUN pip install --upgrade pip

RUN ln -s /usr/bin/python3 /usr/bin/python

RUN mkdir /opt/nodemcu-firmware
WORKDIR /opt/nodemcu-firmware

RUN rm -rf /root
RUN ln -s /tmp /root
ENV PATH="/opt:${PATH}"

COPY cmd.sh /opt/
#COPY read.me /opt/
COPY build /opt/
COPY build-esp32 /opt/
COPY build-esp8266 /opt/
COPY configure-esp32 /opt/
COPY lfs-image /opt/
COPY idle.sh /opt/

# Release some space...
###RUN apt-get clean && rm -rf /var/lib/apt/lists/*

CMD ["/opt/idle.sh"]
