#!/bin/bash

# junand 29.03.2020

# TODO check Option --internal
docker network create --driver bridge proxy
docker network create --driver bridge backbone
docker network create --driver bridge metrics
docker network create --driver bridge logging
