# junand 27.10.2019

FROM octoprint/octoprint

RUN apt-get install -y --no-install-recommends \
    socat

COPY socat_run /tmp
RUN mkdir -p /etc/services.d/socat; mv /tmp/socat_run /etc/services.d/socat/run; touch /etc/services.d/socat/down
