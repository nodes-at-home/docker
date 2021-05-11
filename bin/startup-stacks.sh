#!/bin/bash


pushd "$HOME/docker/docker/bin"

./create_networks.sh

STACKS="admin proxy database metrics nodesathome"

for stack in ${STACKS}
do
    ./up.sh ${stack}
done

popd
