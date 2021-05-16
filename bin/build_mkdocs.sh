#!/bin/bash

# junand 16.05.2021

docker run --rm -it -e TZ=Europe/Berlin -v ${PWD}:/docs --name build_mkdocs mkdocs-material build