#!/bin/bash

docker-compose -p hass -f hass.yaml down
docker-compose -p monitoring -f monitoring.yaml down

