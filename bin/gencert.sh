#!/bin/bash

# junand 22.03.2020
# junand 31.03.2020

# TODO
# https://likegeeks.com/linux-bash-scripting-awesome-guide-part3/
# Options:
#   -p <password>
#   -c ca name
#   -w with ca cert creation
#   -s server list (spaceseparated)
#   parameter: server1 server2 ..., without default list

# https://msol.io/blog/tech/create-a-self-signed-ecc-certificate/
# https://www.erianna.com/ecdsa-certificate-authorities-and-certificates-with-openssl/

# defaults
WITH_CA=false
PASSWORD=hallo
CA=nodesathome
SERVERS="nodesathome1 nodesathome2 pibrew pitouch pivpn pisniffer Andreas-Surface piflower pibarcode"

POSITIONAL=()

while [[ $# -gt 0 ]]
do

    key="$1"

    case $key in
        -p|--password)
        PASSWORD="$2"
        shift; shift
        ;;
        -c|--ca)
        CA="$2"
        shift; shift
        ;;
        -w|--withca)
        WITH_CA=true
        shift
        ;;
        -s|--servers)
        SERVERS="$2"
        shift; shift
        ;;
        *)    # unknown option
        POSITIONAL+=("$1") # save it in an array for later
        shift # past argument
        ;;
    esac

done

set -- "${POSITIONAL[@]}" # restore positional parameters

echo "PARAMETER=$*"

echo "PASSWORD      = ${PASSWORD}"
echo "WITH_CA       = ${WITH_CA}"
echo "CA            = ${CA}"
echo "SERVERS       = ${SERVERS}"

# 5 years
DAYS_CA=1825
DAYS_CERT=1825

AES_OPT="-aes128"
SHA_OPT="-sha256"
SUBJ_BASE="/C=DE/L=Panketal/O=Andreas"

PASS="pass:${PASSWORD}"

if [ ${WITH_CA} = true ]
then

    # private key for CA
    # -aes128, -aes192, -aes256, -aria128, -aria192, -aria256, -camellia128, -camellia192, -camellia256, -des, -des3, -idea
    echo "STEP 1 -> generating private key for CA"
    #openssl genrsa ${AES_OPT} -passout ${PASS} -out ca-key-${CA}.pem ${BITLEN}
    openssl ecparam -genkey -name prime256v1 -out ca-key-${CA}.pem

    # root certificate
    # -> invariant to rsa vs. ec
    echo "STEP 2 -> generating root certificate"
    openssl req -x509 -new -nodes -extensions v3_ca -passin ${PASS} -key ca-key-${CA}.pem -days ${DAYS_CA} -out ca-root-${CA}.pem ${SHA_OPT} -subj "${SUBJ_BASE}/CN=${CA}"

fi

# certificates for all servers

echo "STEP 3 -> generating  certificates for servers"
for server in ${SERVERS}
do

    # private key
    echo "STEP 3 $server -> generating private key"
    #openssl genrsa -out certificate-key-${server}.pem ${BITLEN}
    openssl ecparam -genkey -name prime256v1 -out certificate-key-${server}.pem

    # cetificate request
    # -> invariant to rsa vs. ec
    echo "STEP 3 $server -> request certificate"
    openssl req -new -key certificate-key-${server}.pem -out certificate-${server}.csr ${SHA_OPT} -subj "${SUBJ_BASE}/CN=${server}"

    # selfsigned certificate
    # -> invariant to rsa vs. ec
    echo "STEP 3 $server -> sign certificate"
    openssl x509 -req -extfile <(printf "subjectAltName=DNS:${server},DNS:${server}.fritz.box") -in certificate-${server}.csr -CA ca-root-${CA}.pem -CAkey ca-key-${CA}.pem -passin ${PASS} -CAcreateserial -out certificate-pub-${server}.pem -days ${DAYS_CERT} ${SHA_OPT}

done
