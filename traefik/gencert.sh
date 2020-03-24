#!/bin/bash

# junand 22.03.2020


###rm *.pem

[ "x" = "x$1" ] && echo "Fehlender erster Parameter" && exit
PASSWORD=$1
[ -z $PASSOWRD ] && echo "no password" && PASSOWRD="hallo"

CA="nodesathome"
SERVERS="pitest nodesathome1 nodesathome2 pibrew pitouch"

BITLEN=2048

DAYS_CA=1095
DAYS_CERT=365

AES_OPT="-aes128"
SHA_OPT="-sha256"

PASS="pass:${PASSOWRD}"
echo "pass clause: ${PASS}"

# private key for CA
# -aes128, -aes192, -aes256, -aria128, -aria192, -aria256, -camellia128, -camellia192, -camellia256, -des, -des3, -idea
echo "STEP 1 -> generating private key for CA"
openssl genrsa ${AES_OPT} -passout ${PASS} -out ca-key-${CA}.pem ${BITLEN}

# root certificte
echo "STEP 2 -> generating root certificate"
openssl req -x509 -new -nodes -extensions v3_ca -passin ${PASS} -key ca-key-${CA}.pem -days ${DAYS_CA} -out ca-root-${CA}.pem ${SHA_OPT}

# certificates for all servers

echo "STEP 3 -> generating  certificates for servers"
for server in ${SERVERS}
do
    # private key
    echo "STEP 3 $server -> generating private key"
    openssl genrsa -out certificate-key-${server}.pem ${BITLEN}
    # cetificate request
    echo "STEP 3 $server -> request certificate"
    openssl req -new -key certificate-key-${server}.pem -out certificate-${server}.csr ${SHA_OPT}
    # selfsigned certificate
    echo "STEP 3 $server -> sign certificate"
    openssl x509 -req -in certificate-${server}.csr -CA ca-root-${CA}.pem -CAkey ca-key-${CA}.pem -passin ${PASS} -CAcreateserial -out certificate-pub-${server}.pem -days ${DAYS_CERT} ${SHA_OPT}
done