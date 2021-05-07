#!/bin/bash
# junand 20.03.2021

# set admin token here
CONTAINER=influxdb
INFLUX_TOKEN=-iLSqZNSUwzgAl_MbJyjhfNz8C0-kHJd3hKiXXY-hKTu50lSuW4WMNGsnQPNWrKiprbVq_8s7ryKca4uZEtNOg==
PASSWORD=ninanora

function get_bucket_id {
    # $1 bucket name
    docker exec ${CONTAINER} influx bucket list --hide-headers --name $1 | head -n 1 | awk '{ print $1 }'
}

function get_org_id {
    # $1 org name
    docker exec ${CONTAINER} influx org list --hide-headers --name $1 | head -n 1 | awk '{ print $1 }'
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

function rename_bucket {
    # $1 new name
    ID=$(get_bucket_id "$1/autogen")
    if [ "${ID}" != "Error:" ]
    then
        docker exec ${CONTAINER} influx bucket update --id $ID --name $1
    fi
}

echo start

rename_bucket ambient
rename_bucket brewery
rename_bucket consumption
rename_bucket home_assistant
rename_bucket rssi

# read token ids, container must be runnning
BUCKET_ID_AMBIENT=$(get_bucket_id ambient)
BUCKET_ID_BREWERY=$(get_bucket_id brewery)
BUCKET_ID_CONSUMPTION=$(get_bucket_id consumption)
BUCKET_ID_HOME_ASSISTANT=$(get_bucket_id home_assistant)
BUCKET_ID_RSSI=$(get_bucket_id rssi)

echo ""
echo "bucket ids"
echo "ambient:        ${BUCKET_ID_AMBIENT}"
echo "brewery:        ${BUCKET_ID_BREWERY}"
echo "consumption:    ${BUCKET_ID_CONSUMPTION}"
echo "home_assistant: ${BUCKET_ID_HOME_ASSISTANT}"
echo "rssi:           ${BUCKET_ID_RSSI}"


ORGID_NODESATHOME=$(get_org_id nodesathome)

echo ""
echo "org ids"
echo "nodesathome:    ${ORGID_NODESATHOME}"

USER_ID_GRAFANA=$(get_user_id grafana)
USER_ID_HASS=$(get_user_id hass)
USER_ID_NODERED=$(get_user_id nodered)
USER_ID_PIBREW=$(get_user_id pibrew)

echo ""
echo "user ids"
echo "grafana:        ${USER_ID_GRAFANA}"
echo "home-assistant: ${USER_ID_HASS}"
echo "nodered:        ${USER_ID_NODERED}"
echo "pibrew:         ${USER_ID_PIBREW}"

TOKEN_GRAFANA_READ=$(get_token grafana_read grafana "\
--read-bucket ${BUCKET_ID_AMBIENT} \
--read-bucket ${BUCKET_ID_BREWERY} \
--read-bucket ${BUCKET_ID_CONSUMPTION} \
--read-bucket ${BUCKET_ID_HOME_ASSISTANT} \
--read-bucket ${BUCKET_ID_RSSI} \
")

TOKEN_HASS_WRITE=$(get_token hass_write hass "\
--write-bucket ${BUCKET_ID_HOME_ASSISTANT} \
")

TOKEN_NODERED_WRITE=$(get_token nodered_write nodered "\
--write-bucket ${BUCKET_ID_AMBIENT} \
--write-bucket ${BUCKET_ID_CONSUMPTION} \
--write-bucket ${BUCKET_ID_RSSI} \
")

TOKEN_PIBREW_WRITE=$(get_token pibrew_write pibrew "\
--write-bucket ${BUCKET_ID_BREWERY} \
")

echo "token"
echo "grafana_read:   ${TOKEN_GRAFANA_READ}"
echo "hass_write:     ${TOKEN_HASS_WRITE}"
echo "nodered_write:  ${TOKEN_NODERED_WRITE}"
echo "pibrew_write:   ${TOKEN_PIBREW_WRITE}"
