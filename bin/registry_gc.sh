#!/bin/bash

docker exec -it -u root registry registry garbage-collect /var/lib/registry/registry_config.yaml --delete-untagged=true
