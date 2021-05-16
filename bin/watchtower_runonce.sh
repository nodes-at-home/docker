#!/bin/bash

# junand 14.03.2021

docker run --rm -v /var/run/docker.sock:/var/run/docker.sock --name watchtower_once containrrr/watchtower --run-once