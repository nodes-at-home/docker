#!/bin/bash

docker-compose -p monitoring -f monitoring.yaml up -d
docker-compose -p hass -f hass.yaml up -d

