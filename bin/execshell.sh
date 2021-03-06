#!/bin/bash

[ -z "$1" ] && echo "ERROR: first parameter must bee the app to execute!" && exit

pushd "$HOME/docker/docker"

APP=$1
STACK=`grep "${APP}:$" ./*/docker-compose.yaml | cut -d/ -f2`

echo "Executing $APP in $STACK"

[ -n "$APP" ] && [ -n "$STACK" ] && [ -d ./"$TACK" ] && cd $STACK && docker-compose exec $APP bash && cd -

popd

# remove images who are older than ...
# docker system prune --filter "until=240h"
