#!/bin/bash

[ -z "$1" ] && echo "ERROR: first parameter must bee the app to build!" && exit

APP=$1
STACK=`grep "${APP}:$" ./*/docker-compose.yaml | cut -d/ -f2`

echo "Building $APP in $STACK"

[ -n "$APP" ] && [ -n "$STACK" ] && [ -d ./"$TACK" ] && cd $STACK && docker-compose build $APP && cd -

# remove images who are older than ...
# docker system prune --filter "until=240h"
