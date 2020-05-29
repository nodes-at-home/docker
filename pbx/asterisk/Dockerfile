# junand 23.05.2020

# base image from https://www.balena.io/docs/reference/base-images/base-images/
# insprations from https://hub.docker.com/r/hilschernetpi/netpi-bluetooth/dockerfile

# https://github.com/moby/moby/issues/16208

FROM        balenalib/armv7hf

MAINTAINER  junand

ENV         UDEV=1

RUN         apt-get update && apt-get install -y --no-install-recommends \
            asterisk \
            asterisk-mobile \
            usbutils \
            bluez \
            && apt-get clean \
            && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*            
            
CMD         [ "balena-idle", "--silent" ]

