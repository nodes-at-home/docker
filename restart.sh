#!/bin/bash

[ -z "$1" ] && echo "ERROR: first parameter must bee the app to restart!" && exit

APP=$1
STACK=`grep "${APP}:$" ./*/docker-compose.yaml | cut -d/ -f2`

echo "Restarting $APP in $STACK"

[ -n "$APP" ] && [ -n "$STACK" ] && [ -d ./"$TACK" ] && cd $STACK && docker-compose stop $APP && docker-compose up -d --no-deps $APP && cd -

# remove images who are older than ...
# docker system prune --filter "until=240h"
