# junand 27.10.2019

FROM reloxx13/octoprint

RUN apt-get install -y --no-install-recommends \
    socat

COPY supervisord_socat.conf /tmp
RUN cat /tmp/supervisord_socat.conf >> /etc/supervisor/supervisord.conf; rm -f /tmp/supervisord_socat.conf
