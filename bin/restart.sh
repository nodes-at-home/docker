#!/bin/bash

if [ -x /usr/bin/docker-compose ]
then
    COMPOSE=docker-compose
else
    COMPOSE="docker compose"
fi

[ -z "$1" ] && echo "ERROR: first parameter must bee the app to restart!" && exit

pushd "$HOME/docker/docker"

APP=$1
STACK=`grep "${APP}:$" ./*/docker-compose.yaml | cut -d/ -f2`

echo "Restarting $APP in $STACK"

[ -n "$APP" ] && [ -n "$STACK" ] && [ -d ./"$STACK" ] && cd $STACK && $COMPOSE stop $APP && $COMPOSE up -d --no-deps $APP && cd -

popd

# remove images who are older than ...
# docker system prune --filter "until=240h"
