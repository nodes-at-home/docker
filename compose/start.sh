#!/bin/bash

docker-compose -p monitoring -f monitoring.yaml start
docker-compose -p hass -f hass.yaml start

