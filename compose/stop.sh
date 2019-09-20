#!/bin/bash

docker-compose -p hass -f hass.yaml stop
docker-compose -p monitoring -f monitoring.yaml stop

