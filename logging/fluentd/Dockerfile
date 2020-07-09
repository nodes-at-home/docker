# junand 29.03.2020

# from ct 08/2020 S. 166
# https://github.com/jamct/docker-log
# https://hub.docker.com/r/kiyoto/docker-fluentd

FROM fluent/fluentd:v1.11-arm64-debian

USER root
RUN ["/usr/local/bin/gem", "install", "fluent-plugin-record-reformer", "fluent-plugin-elasticsearch", "fluent-plugin-rewrite-tag-filter", "--no-document"]

# make pos file write- and readable for fluent
# this is only necessary for a fluent container runnning under user fluent, its maybe a bug in fluent (image)
RUN touch /var/log/fluentd-docker.pos; chown fluent.fluent /var/log/fluentd-docker.pos

###USER fluent # docker logs are only readable under root
