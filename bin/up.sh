#!/bin/bash

if [ -x /usr/bin/docker-compose ]
then
    COMPOSE=docker-compose
else
    COMPOSE="docker compose"
fi

[ -z "$1" ] && echo "ERROR: first parameter must be the stack to start!" && exit 1

pushd "$HOME/docker/docker"

STACK=$1

echo "Bringing up $STACK"

[ -n "$STACK" ] && [ -d ./"$STACK" ] && cd $STACK && $COMPOSE up -d && cd - && popd && exit 0

popd

exit 1

# remove images who are older than ...
# docker system prune --filter "until=240h"
