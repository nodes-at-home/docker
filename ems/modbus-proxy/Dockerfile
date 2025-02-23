###
### junand 20.05.2023
### adapted from https://github.com/tiagocoutinho/modbus-proxy
###

FROM python:3.8-alpine

USER root

WORKDIR /app

COPY . /app

# install dependencies to the local user directory
RUN pip --disable-pip-version-check --no-input --no-cache-dir --timeout 3 install pyyaml
RUN pip --disable-pip-version-check --no-input --no-cache-dir --timeout 3 install modbus-proxy[yaml]

ENTRYPOINT ["modbus-proxy", "-c", "modbus-proxy.yaml"]

