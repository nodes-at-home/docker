#!/bin/bash


pushd "$HOME/docker/docker"

./create_networks.sh

STACKS="admin proxy database metrics logging nodesathome"

for stack in ${STACKS}
do
    ./up.sh ${stack}
done

popd
