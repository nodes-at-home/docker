#!/bin/bash

# junand 14.03.2021

# possible options --dubug --trace
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v ~/.docker/config.json:/config.json --name watchtower_once containrrr/watchtower --run-once $@
