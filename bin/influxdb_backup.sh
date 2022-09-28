#!/bin/bash

# junand 27.09.2022

docker exec influxdb influx backup /var/lib/influxdb2/backup/influxdb_${HOSTNAME}_backup_$(date '+%Y-%m-%d_%H-%M') -t=${INFLUX_TOKEN}
