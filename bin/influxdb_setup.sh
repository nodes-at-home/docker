#!/bin/bash

# junand 27.09.2022

[ -z "${INFLUX_TOKEN}" ]    && echo Token fehlt && exit 1
[ -z "${INFLUX_ORG}" ]      && echo Organisation fehlt && exit 1
[ -z "${INFLUX_USER}" ]     && echo User fehlt && exit 1
[ -z "${INFLUX_PASSWORD}" ] && echo Passwort fehlt && exit 1

docker exec influxdb influx setup --token=${INFLUX_TOKEN} --org ${INFLUX_ORG} --bucket bucket0 --username ${INFLUX_USER} --password ${INFLUX_PASSWORD} --force