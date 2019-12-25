#!/bin/bash

[ -z "$1" ] && echo "ERROR: first parameter must bee the app to restart!" && exit

APP=$1
echo "Restarting $APP"

[ -n "$APP" ] && docker-compose stop $APP && docker-compose up -d --no-deps $APP

# remove images who are older than ...
# docker system prune --filter "until=240h"