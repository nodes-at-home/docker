#!/bin/bash

# junand 27.09.2022

[ -z "$1" ] && echo Dateiname des Backups fehlt && exit 1

docker exec influxdb influx restore --full /var/lib/influxdb2/backup/$1