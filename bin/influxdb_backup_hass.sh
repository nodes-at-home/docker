#!/bin/bash

# junand 05.09.2023

set -ex

source /home/pi/.local/bashrc_env

BACKUP_BUCKET=home_assistant
BACKUP_NAME=influxdb_${HOSTNAME}_${BACKUP_BUCKET}_$(date '+%Y-%m-%d_%H-%M')
BACKUP_PATH=/home/pi/docker/influxdb/v2/backup

###[ -z ${INFLUX_TOKEN} ] && INFLUX_TOKEN=`grep INFLUX_TOKEN /home/pi/.local/bashrc_env | awk -F = '{ print $2 }'`
echo ${INFLUX_TOKEN}

docker exec influxdb influx backup --bucket ${BACKUP_BUCKET} /var/lib/influxdb2/backup/${BACKUP_NAME} -t=${INFLUX_TOKEN}

cd ${BACKUP_PATH}
echo `pwd`

sudo zip -r ${BACKUP_NAME}.zip ${BACKUP_NAME}
sudo rm -rf ${BACKUP_NAME}

/usr/bin/rclone --config="/home/pi/.config/rclone/rclone.conf" move ${BACKUP_NAME}.zip backup:Backup
