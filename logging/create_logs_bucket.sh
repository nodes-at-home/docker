#!/bin/bash
# junand 23.03.2021

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


BUCKET_ID_LOGS=$(get_bucket_id logs)

echo ""
echo "bucket ids"
echo "logs:             ${BUCKET_ID_LOGS}"

USER_ID_LOGS=$(get_user_id logs)

echo ""
echo "user ids"
echo "logs:             ${USER_ID_LOGS}"


TOKEN_LOGS_READ_WRITE=$(get_token logs_read_write logs "\
--read-bucket ${BUCKET_ID_LOGS} \
--write-bucket ${BUCKET_ID_LOGS} \
")

echo ""
echo "token"
echo "logs_read_write:  ${TOKEN_LOGS_READ_WRITE}"
