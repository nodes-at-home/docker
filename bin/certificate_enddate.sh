#!/bin/bash

DIR=~/docker/traefik/ssl

POSITIONAL=()

while [[ $# -gt 0 ]]
do

    key="$1"

    case $key in
        -d|--directory)
        DIR="$2"
        shift; shift
        ;;
        *)    # unknown option
        POSITIONAL+=("$1") # save it in an array for later
        shift # past argument
        ;;
    esac

done

set -- "${POSITIONAL[@]}" # restore positional parameters

# echo "PARAMETER=$*"
# echo "POSITIONAL=${POSITIONAL}"

[ -n "${POSITIONAL}" ] && DIR=${POSITIONAL}

echo -n "${DIR}/ca-root-nodesathome.pem: "
openssl x509 -enddate -noout -in ${DIR}/ca-root-nodesathome.pem

find ${DIR} -name 'certificate-pub-*.pem' -exec echo -n '{}: ' \; -exec openssl x509 -enddate -noout -in '{}' \;
