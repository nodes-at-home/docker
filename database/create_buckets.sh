#!/bin/bash
# junand 05.04.2021

CONTAINER=influxdb
# INFLUX_TOKEN=***Secret***
# PASSWORD=***Secret***

function get_bucket_id {
    # $1 bucket name
    RESULT=`docker exec ${CONTAINER} influx bucket list --hide-headers --name $1 | head -n 1 | awk '{ print $1 }'`
    if [ "${RESULT}" == "Error:" ]
    then
        RESULT=`docker exec ${CONTAINER} influx bucket create --hide-headers --name $1 --org nodesathome  | head -n 1 | awk '{ print $1 }'`
    fi
    echo ${RESULT}

}

function get_user_id {
    # $1 user name
    RESULT=`docker exec ${CONTAINER} influx user list --hide-headers --name $1 | head -n 1 | awk '{ print $1 }'`
    if [ "${RESULT}" == "Error:" ]
    then
        RESULT=`docker exec ${CONTAINER} influx user create --hide-headers --name $1 --password ${PASSWORD} | head -n 1 | awk '{ print $1 }'`
    fi
    echo ${RESULT}
}

function get_token {
    # $1 description $2 username
    RESULT=`docker exec ${CONTAINER} influx auth list --hide-headers | grep $1 | head -n 1 | awk '{ print $3 }'`
    if [ -z "${RESULT}" ]
    then
        RESULT=`docker exec ${CONTAINER} influx auth create --hide-headers --org nodesathome --description $1 --user $2 $3 -t ${INFLUX_TOKEN} | head -n 1 | awk '{ print $3 }'`
    fi
    echo ${RESULT}
}

function set_retention {
    # $1 bucket id $2 retentions string
    docker exec ${CONTAINER} influx bucket update --id $1 --retention $2
}

function list_buckets {
    # $1 id
    docker exec ${CONTAINER} influx bucket list
}


BUCKET_ID_LOGS=$(get_bucket_id logs)
BUCKET_ID_TELEGRAF=$(get_bucket_id telegraf)
BUCKET_ID_FRITZBOX=$(get_bucket_id fritzbox)

echo ""
echo "bucket ids"
echo "logs:             ${BUCKET_ID_LOGS}"
echo "telegraf:         ${BUCKET_ID_TELEGRAF}"
echo "fritzbox:         ${BUCKET_ID_FRITZBOX}"

USER_ID_LOGS=$(get_user_id logs)
USER_ID_TELEGRAF=$(get_user_id telegraf)
USER_ID_FRITZBOX=$(get_user_id fritzbox)

echo ""
echo "user ids"
echo "logs:             ${USER_ID_LOGS}"
echo "telegraf:         ${USER_ID_TELEGRAF}"
echo "fritzbox:         ${USER_ID_FRITZBOX}"


TOKEN_LOGS_READ_WRITE=$(get_token logs_read_write logs "\
--read-bucket ${BUCKET_ID_LOGS} \
--write-bucket ${BUCKET_ID_LOGS} \
")

TOKEN_TELEGRAF_READ_WRITE=$(get_token telegraf_read_write telegraf "\
--read-bucket ${BUCKET_ID_TELEGRAF} \
--write-bucket ${BUCKET_ID_TELEGRAF} \
")

TOKEN_FRITZBOX_READ_WRITE=$(get_token fritzbox_read_write fritzbox "\
--read-bucket ${BUCKET_ID_FRITZBOX} \
--write-bucket ${BUCKET_ID_FRITZBOX} \
")

echo ""
echo "token"
echo "logs_read_write:  ${TOKEN_LOGS_READ_WRITE}"
echo "telegraf_read_write:  ${TOKEN_TELEGRAF_READ_WRITE}"
echo "fritzbox_read_write:  ${TOKEN_FRITZBOX_READ_WRITE}"


_=$(set_retention ${BUCKET_ID_LOGS} "4w")
_=$(set_retention ${BUCKET_ID_TELEGRAF} "1w")
_=$(set_retention ${BUCKET_ID_FRITZBOX} "4w")

echo ""
echo "set retention"
list_buckets
